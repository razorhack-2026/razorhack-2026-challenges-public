import crypto from 'node:crypto'
import express from 'express'
import rateLimit from 'express-rate-limit'
import {
    BULK_DISCOUNT_MAX_RATE,
    BULK_DISCOUNT_MIN_QTY,
    BULK_DISCOUNT_SCALE,
    BULK_ORDER_PROFIT_CAP,
    commodities,
    commodityHistory,
    listings,
    marketStats,
    QUOTE_LOCK_PROFIT_CAP,
    QUOTE_LOCK_TTL_MS,
    SELL_CLEARING_FEE_RATE,
    STARTER_CREDITS,
    STARTER_HOLDINGS,
    startMarketSimulation,
    VOUCHER_CREDIT_BONUS,
} from './data.js'

const FLUX_CAPACITOR_LISTING_ID = 'listing-7'

const app = express()
// Only reachable through the frontend's nginx proxy (one hop), so trust its
// X-Forwarded-For for req.ip. The rate limiters key on the session, not IP.
app.set('trust proxy', 1)
app.disable('x-powered-by')
app.use(express.json())

const SESSION_COOKIE = 'zgs_session'
const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30

const accounts = new Map()

// Server-only trading-integrity ledger: tracks per-session program ceilings and
// lockdown state.
const ledger = new Map()

// Server-only quote-lock store: quoteId -> { sessionId, ticker, qty, price, expiresAt }
const quotes = new Map()

// Quotes that are locked but never executed or canceled would otherwise live
// forever; sweep expired ones periodically.
const QUOTE_SWEEP_INTERVAL_MS = 60 * 1000
setInterval(() => {
    const now = Date.now()
    for (const [quoteId, quote] of quotes) {
        if (now > quote.expiresAt) quotes.delete(quoteId)
    }
}, QUOTE_SWEEP_INTERVAL_MS).unref()

function roundCredits(value) {
    return Math.round(value * 100) / 100
}

function getLedger(sessionId) {
    if (!ledger.has(sessionId)) {
        ledger.set(sessionId, {
            voucherRedeemed: false,
            bulkOrderProfitBanked: 0,
            bulkOrderLocked: false,
            quoteLockProfitBanked: 0,
            quoteLockLocked: false,
            listingPurchases: {},
            fluxCapacitorPurchased: false,
        })
    }
    return ledger.get(sessionId)
}

function parseCookies(header) {
    const cookies = {}
    if (!header) return cookies
    for (const part of header.split(';')) {
        const separator = part.indexOf('=')
        if (separator === -1) continue
        const key = part.slice(0, separator).trim()
        const value = part.slice(separator + 1).trim()
        cookies[key] = decodeURIComponent(value)
    }
    return cookies
}

function createAccount() {
    const holdings = {}
    for (const c of commodities) {
        holdings[c.ticker] = STARTER_HOLDINGS[c.ticker] ?? 0
    }
    return { credits: STARTER_CREDITS, holdings }
}

app.use((req, res, next) => {
    const cookies = parseCookies(req.headers.cookie)
    let sessionId = cookies[SESSION_COOKIE]
    if (!sessionId || !accounts.has(sessionId)) {
        sessionId = crypto.randomUUID()
        accounts.set(sessionId, createAccount())
        res.setHeader(
            'Set-Cookie',
            `${SESSION_COOKIE}=${sessionId}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${SESSION_MAX_AGE_SECONDS}`,
        )
    }
    req.sessionId = sessionId
    req.account = accounts.get(sessionId)
    req.ledger = getLedger(sessionId)
    next()
})

// Caps how often a single player can poll live-data endpoints, independent of
// whatever refresh interval the client happens to use.
const liveDataLimiter = rateLimit({
    windowMs: 1000,
    limit: 15,
    standardHeaders: true,
    legacyHeaders: false,
    keyGenerator: (req) => req.sessionId,
})

app.use('/api/commodities', liveDataLimiter)
app.use('/api/stats', liveDataLimiter)

// Trades "settle through a clearing partner" and are paced accordingly.
const tradeLimiter = rateLimit({
    windowMs: 1000,
    limit: 5,
    standardHeaders: true,
    legacyHeaders: false,
    keyGenerator: (req) => req.sessionId,
})

app.use('/api/trade', tradeLimiter)
app.use('/api/quote', tradeLimiter)

app.get('/api/commodities', (_req, res) => {
    res.json(commodities)
})

app.get('/api/stats', (_req, res) => {
    res.json(marketStats)
})

app.get('/api/commodities/:ticker', (req, res) => {
    const ticker = req.params.ticker.toUpperCase()
    const commodity = commodities.find((c) => c.ticker === ticker)
    if (!commodity) {
        return res.status(404).json({ error: 'Unknown ticker' })
    }
    res.json(commodity)
})

app.get('/api/commodities/:ticker/history', (req, res) => {
    const ticker = req.params.ticker.toUpperCase()
    const history = commodityHistory[ticker]
    if (!history) {
        return res.status(404).json({ error: 'Unknown ticker' })
    }
    res.json(history)
})

app.get('/api/listings', (req, res) => {
    const purchased = req.ledger.listingPurchases
    res.json(
        listings.map((l) => {
            const ownedByYou = purchased[l.id] ?? 0
            const entry = { ...l, qty: Math.max(0, l.qty - ownedByYou), ownedByYou }
            if (l.id === FLUX_CAPACITOR_LISTING_ID && ownedByYou > 0 && process.env.FLAG) {
                entry.flag = process.env.FLAG
            }
            return entry
        }),
    )
})

app.get('/api/account', (req, res) => {
    res.json(req.account)
})

app.get('/api/session', (req, res) => {
    res.json({ sessionId: req.sessionId })
})

// Lets a trader walk away from their current account and start a fresh one
// with the standard starting stake.
app.post('/api/session/reset', (req, res) => {
    accounts.delete(req.sessionId)
    ledger.delete(req.sessionId)
    res.setHeader('Set-Cookie', `${SESSION_COOKIE}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0`)
    res.json({ reset: true })
})

// New-trader signup voucher, Single-use per account.
app.post('/api/voucher/redeem', async (req, res) => {
    const entry = req.ledger

    if (entry.voucherRedeemed) {
        return res.status(409).json({ error: 'Voucher already redeemed' })
    }
    entry.voucherRedeemed = true

    // Simulated async ledger verification (e.g. a fleet-HQ fraud check).
    await new Promise((resolve) => setTimeout(resolve, 1000))

    req.account.credits += VOUCHER_CREDIT_BONUS

    res.json({ granted: VOUCHER_CREDIT_BONUS, credits: req.account.credits })
})

// Buying always goes through Quote Lock (see below). Sales settle at the live
// index price less the clearing fee.
app.post('/api/trade/sell', (req, res) => {
    const ticker = String(req.body?.ticker || '').toUpperCase()
    const qty = Number(req.body?.qty)
    const commodity = commodities.find((c) => c.ticker === ticker)
    if (!commodity || !(qty > 0)) {
        return res.status(400).json({ error: 'Invalid trade' })
    }

    const held = req.account.holdings[ticker] ?? 0
    if (qty > held) {
        return res.status(400).json({ error: 'Insufficient holdings' })
    }

    const gross = roundCredits(qty * commodity.pricePerTon)
    const fee = roundCredits(gross * SELL_CLEARING_FEE_RATE)
    const proceeds = roundCredits(gross - fee)

    req.account.holdings[ticker] = held - qty
    req.account.credits += proceeds

    res.json({ proceeds, fee, credits: req.account.credits, holdings: req.account.holdings[ticker] })
})

// Bulk Order Discount Program. Orders of BULK_DISCOUNT_MIN_QTY+ tons qualify
// for a volume discount off the live index price, scaling with order size up
// to BULK_DISCOUNT_MAX_RATE, capped at BULK_ORDER_PROFIT_CAP of savings.
// The 500-ton order minimum and the positive-quantity requirement are only
// enforced in the trading terminal's UI - this endpoint accepts (and prices)
// any nonzero quantity exactly as submitted, sign included. A negative
// quantity produces a negative cost, which credits the account.
app.post('/api/trade/bulk-buy', (req, res) => {
    if (req.ledger.bulkOrderLocked) {
        return res.status(429).json({
            error: 'Weekly Bulk Order savings limit reached. Check back next week.',
        })
    }

    const ticker = String(req.body?.ticker || '').toUpperCase()
    const qty = Number(req.body?.qty)
    const commodity = commodities.find((c) => c.ticker === ticker)
    if (!commodity || !Number.isFinite(qty) || qty === 0) {
        return res.status(400).json({ error: 'Invalid bulk order' })
    }

    const discountRate =
        qty >= BULK_DISCOUNT_MIN_QTY ? Math.min(BULK_DISCOUNT_MAX_RATE, qty / BULK_DISCOUNT_SCALE) : 0
    const listCost = roundCredits(qty * commodity.pricePerTon)
    let cost = roundCredits(qty * commodity.pricePerTon * (1 - discountRate))

    // Everything the account gains relative to paying list price counts toward
    // the weekly savings ceiling: the discount on an eligible order, or the
    // whole credit on a negative-cost one.
    const savings = cost < 0 ? -cost : Math.max(0, listCost - cost)
    let banked = 0
    if (savings > 0) {
        const remaining = Math.max(0, BULK_ORDER_PROFIT_CAP - req.ledger.bulkOrderProfitBanked)
        banked = Math.min(savings, remaining)
        cost = cost < 0 ? -banked : roundCredits(listCost - banked)
    }

    if (cost > req.account.credits) {
        return res.status(402).json({ error: 'Insufficient credits' })
    }

    // Only commit savings once the order is known to fill.
    req.ledger.bulkOrderProfitBanked = roundCredits(req.ledger.bulkOrderProfitBanked + banked)
    if (req.ledger.bulkOrderProfitBanked >= BULK_ORDER_PROFIT_CAP) {
        req.ledger.bulkOrderLocked = true
    }

    req.account.credits -= cost
    req.account.holdings[ticker] = (req.account.holdings[ticker] ?? 0) + qty

    res.json({ cost, credits: req.account.credits, holdings: req.account.holdings[ticker] })
})

// Quote Lock. Lets a trader lock the current price on a quantity for
// QUOTE_LOCK_TTL_MS before executing. The quantity and ticker locked in
// are always read from the server-held quote - but execution price is trusted
// from the client's settlement instruction instead of the price the quote
// actually locked in.
app.post('/api/quote/lock', (req, res) => {
    if (req.ledger.quoteLockLocked) {
        return res.status(423).json({
            error: 'Quote Lock suspended for this account pending anomaly review.',
        })
    }

    const ticker = String(req.body?.ticker || '').toUpperCase()
    const qty = Number(req.body?.qty)
    const commodity = commodities.find((c) => c.ticker === ticker)
    if (!commodity || !Number.isFinite(qty) || !(qty > 0)) {
        return res.status(400).json({ error: 'Invalid quote request' })
    }

    const quoteId = crypto.randomUUID()
    const expiresAt = Date.now() + QUOTE_LOCK_TTL_MS
    quotes.set(quoteId, { sessionId: req.sessionId, ticker, qty, price: commodity.pricePerTon, expiresAt })

    res.json({ quoteId, ticker, qty, price: commodity.pricePerTon, expiresAt })
})

app.post('/api/quote/execute', (req, res) => {
    if (req.ledger.quoteLockLocked) {
        return res.status(423).json({
            error: 'Quote Lock suspended for this account pending anomaly review.',
        })
    }

    const quoteId = String(req.body?.quoteId || '')
    const quote = quotes.get(quoteId)
    if (!quote || quote.sessionId !== req.sessionId) {
        return res.status(404).json({ error: 'Quote not found' })
    }
    if (Date.now() > quote.expiresAt) {
        quotes.delete(quoteId)
        return res.status(410).json({ error: 'Quote expired' })
    }

    const price = Number(req.body?.price)
    if (!(price > 0)) {
        return res.status(400).json({ error: 'Invalid quote execution' })
    }

    const fairCost = roundCredits(quote.qty * quote.price)
    const cost = roundCredits(quote.qty * price)
    const gain = Math.max(0, fairCost - cost)

    let banked = 0
    let finalCost = fairCost
    if (gain > 0) {
        const remaining = Math.max(0, QUOTE_LOCK_PROFIT_CAP - req.ledger.quoteLockProfitBanked)
        banked = Math.min(gain, remaining)
        finalCost = roundCredits(fairCost - banked)
    }

    if (finalCost > req.account.credits) {
        return res.status(402).json({ error: 'Insufficient credits' })
    }

    // Only commit the deviation once the trade is known to settle, so a
    // rejected execution can't trip the anomaly review on its own.
    req.ledger.quoteLockProfitBanked = roundCredits(req.ledger.quoteLockProfitBanked + banked)
    if (req.ledger.quoteLockProfitBanked >= QUOTE_LOCK_PROFIT_CAP) {
        req.ledger.quoteLockLocked = true
    }

    quotes.delete(quoteId)
    req.account.credits -= finalCost
    req.account.holdings[quote.ticker] = (req.account.holdings[quote.ticker] ?? 0) + quote.qty

    res.json({ cost: finalCost, credits: req.account.credits, holdings: req.account.holdings[quote.ticker] })
})

app.post('/api/quote/cancel', (req, res) => {
    const quoteId = String(req.body?.quoteId || '')
    const quote = quotes.get(quoteId)
    if (!quote || quote.sessionId !== req.sessionId) {
        return res.status(404).json({ error: 'Quote not found' })
    }
    quotes.delete(quoteId)
    res.json({ canceled: true })
})

app.post('/api/listings/:id/purchase', (req, res) => {
    const listing = listings.find((l) => l.id === req.params.id)
    if (!listing) {
        return res.status(404).json({ error: 'Listing unavailable' })
    }

    const purchased = req.ledger.listingPurchases[listing.id] ?? 0
    if (purchased >= listing.qty) {
        return res.status(409).json({ error: 'Sold out' })
    }
    if (req.account.credits < listing.askPrice) {
        return res.status(402).json({ error: 'Insufficient credits' })
    }

    req.account.credits -= listing.askPrice
    req.ledger.listingPurchases[listing.id] = purchased + 1

    const response = { purchased: true, credits: req.account.credits, item: listing.title }
    if (listing.id === FLUX_CAPACITOR_LISTING_ID) {
        req.ledger.fluxCapacitorPurchased = true
        if (process.env.FLAG) {
            response.flag = process.env.FLAG
        }
    }
    res.json(response)
})

app.post('/api/listings/:id/return', (req, res) => {
    const listing = listings.find((l) => l.id === req.params.id)
    if (!listing) {
        return res.status(404).json({ error: 'Listing unavailable' })
    }
    if (listing.returnable === false) {
        return res.status(400).json({ error: 'This item is not returnable' })
    }

    const purchased = req.ledger.listingPurchases[listing.id] ?? 0
    if (purchased <= 0) {
        return res.status(400).json({ error: "You haven't purchased this listing" })
    }

    req.ledger.listingPurchases[listing.id] = purchased - 1
    req.account.credits += listing.askPrice

    res.json({ returned: true, credits: req.account.credits, item: listing.title })
})

startMarketSimulation()

const port = process.env.PORT || 3001
app.listen(port, '127.0.0.1', () => console.log(`listening on 127.0.0.1:${port}`))
