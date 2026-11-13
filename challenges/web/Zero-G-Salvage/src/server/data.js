export const STARTER_CREDITS = 5000

export const STARTER_HOLDINGS = {
    STEEL: 40,
    IRON: 25,
}

export const VOUCHER_CREDIT_BONUS = 3000

// Clearing fee withheld from every sale. Together with the low tick
// volatility below, it keeps honest buy-low/sell-high trading (including
// using Quote Lock's 15s window as a free look-ahead) from ever turning a
// profit, so market trading can't stand in for either bug.
export const SELL_CLEARING_FEE_RATE = 0.02

// Economy exploit ceilings. The Bulk Order and Quote Lock programs are each
// capped independently so that starting credits (5,000) plus the voucher
// (3,000) plus liquidating the starter holdings (~10,700 at reference prices,
// ~10,490 after the clearing fee) plus either program alone (~26,300-26,500)
// still falls short of FLUX_CAPACITOR_PRICE; only combining both programs
// (~34,300) clears it. The Quote Lock gain is realized by selling a lot back,
// so the fee trims it slightly; the Bulk Order gain is credited directly.
// Once a program's cap is reached it locks down entirely for the account
// (see server.js).
//
// The discount tier only applies at BULK_DISCOUNT_MIN_QTY+ tons. The cheapest
// 500-ton order (~70,000 cr) is far beyond any pre-exploit balance, so honest
// bulk orders can't be resold at the index for profit.
export const BULK_DISCOUNT_MIN_QTY = 500
export const BULK_DISCOUNT_MAX_RATE = 0.4
export const BULK_DISCOUNT_SCALE = 50000
export const BULK_ORDER_PROFIT_CAP = 8000

export const QUOTE_LOCK_TTL_MS = 15000
export const QUOTE_LOCK_PROFIT_CAP = 8000

export const FLUX_CAPACITOR_PRICE = 30000

export const commodities = [
    { ticker: 'STEEL', name: 'Scrap Steel', pricePerTon: 180.13, changePct: 0.8, volumeTons: 4120 },
    { ticker: 'IRON', name: 'Salvaged Iron', pricePerTon: 140.51, changePct: -0.4, volumeTons: 5860 },
    { ticker: 'COPR', name: 'Reclaimed Copper', pricePerTon: 4250, changePct: 2.6, volumeTons: 612 },
    { ticker: 'ALUM', name: 'Aluminum Alloy', pricePerTon: 2105.7, changePct: -1.3, volumeTons: 980 },
    { ticker: 'TITN', name: 'Titanium Scrap', pricePerTon: 9603.33, changePct: 3.1, volumeTons: 214 },
    { ticker: 'REAL', name: 'Rare-Earth Alloy', pricePerTon: 41264.89, changePct: 5.9, volumeTons: 38 },
    { ticker: 'POLY', name: 'Composite Polymer', pricePerTon: 955.43, changePct: -2.1, volumeTons: 723 },
    { ticker: 'SILI', name: 'Silicon Wafer Scrap', pricePerTon: 11809.11, changePct: 4.4, volumeTons: 96 },
]

// Server-only: how often live prices tick. Never exposed to clients.
const TICK_INTERVAL_MS = 1000

// Per-tick price model: pull back toward the reference price plus uniform
// noise of +/-0.1%. Prices settle within roughly +/-0.15% (1 sd) of the
// reference - far inside the 2% clearing fee, so no round trip is
// profitable. The chart auto-scales, so the curve still looks lively.
const PRICE_MEAN_REVERSION = 0.08
const PRICE_NOISE_AMPLITUDE = 0.002

// How far back price history is retained for charting. Every tick appends a
// point and prunes anything older than this window.
const HISTORY_WINDOW_MINUTES = 60
const HISTORY_WINDOW_MS = HISTORY_WINDOW_MINUTES * 60 * 1000

function formatHistoryTimestamp(date) {
    return date.toISOString().slice(11, 19)
}

function buildHistory(currentPrice) {
    const pointCount = Math.floor(HISTORY_WINDOW_MS / TICK_INTERVAL_MS)
    const now = Date.now()

    const prices = [currentPrice]
    let price = currentPrice
    for (let i = 0; i < pointCount; i++) {
        const deviation = (price - currentPrice) / currentPrice
        const meanReversion = -deviation * PRICE_MEAN_REVERSION
        const noise = (Math.random() - 0.5) * PRICE_NOISE_AMPLITUDE
        price = Math.max(1, price * (1 + meanReversion + noise))
        prices.push(price)
    }
    prices.reverse()

    return prices.map((price, i) => {
        const timestamp = now - (pointCount - i) * TICK_INTERVAL_MS
        return {
            date: formatHistoryTimestamp(new Date(timestamp)),
            price: Math.round(price * 100) / 100,
            timestamp,
        }
    })
}

export const commodityHistory = Object.fromEntries(
    commodities.map((c) => [c.ticker, buildHistory(c.pricePerTon)]),
)

for (const c of commodities) {
    const oldest = commodityHistory[c.ticker][0].price
    c.changePct = Math.round(((c.pricePerTon - oldest) / oldest) * 1000) / 10
}

// Fixed anchor each ticker drifts around.
const referencePrices = Object.fromEntries(commodities.map((c) => [c.ticker, c.pricePerTon]))

// Cosmetic homepage stats.
export const marketStats = {
    tonsCleared: 12660,
    verifiedHaulers: 340,
    volumeCr: 2_100_000,
}

function tickStats() {
    marketStats.tonsCleared += Math.floor(Math.random() * 10) + 1
    if (Math.random() < 0.08) {
        marketStats.verifiedHaulers += 1
    }
    marketStats.volumeCr += Math.floor(Math.random() * 12_500) + 250
}

function tickMarket() {
    const now = Date.now()
    const cutoff = now - HISTORY_WINDOW_MS
    for (const c of commodities) {
        const reference = referencePrices[c.ticker]
        const deviation = (c.pricePerTon - reference) / reference
        const meanReversion = -deviation * PRICE_MEAN_REVERSION
        const noise = (Math.random() - 0.5) * PRICE_NOISE_AMPLITUDE
        const nextPrice = c.pricePerTon * (1 + meanReversion + noise)
        c.pricePerTon = Math.max(0.01, Math.round(nextPrice * 100) / 100)

        const history = commodityHistory[c.ticker]
        history.push({ date: formatHistoryTimestamp(new Date(now)), price: c.pricePerTon, timestamp: now })
        while (history.length && history[0].timestamp < cutoff) {
            history.shift()
        }

        const oldest = history[0].price
        c.changePct = Math.round(((c.pricePerTon - oldest) / oldest) * 1000) / 10
    }
}

export function startMarketSimulation() {
    setInterval(() => {
        tickMarket()
        tickStats()
    }, TICK_INTERVAL_MS)
}

export const listings = [
    {
        id: 'listing-1',
        title: 'Class-IV Nav Computer, gimbal intact',
        category: 'Nav & Avionics',
        grade: 'Reclaimed',
        askPrice: 4200,
        qty: 6,
        seller: 'DRIFTWOOD_77',
        origin: 'unlisted origin',
        description:
            'Pulled from a decommissioned courier. Gimbal calibrates clean and ' +
            'firmware has been wiped and reflashed to stock.',
    },
    {
        id: 'listing-2',
        title: 'EVA Suit, size M, seals re-flashed',
        category: 'EVA Suits & Life Support',
        grade: 'Flight-Worthy',
        askPrice: 1850,
        qty: 3,
        seller: 'HOLLOWPOINT',
        origin: 'fleet auction lot 09',
        description:
            'Fleet-surplus suit, seal integrity re-tested to spec. Previous ' +
            "owner's patch kit is still taped inside the thigh pocket.",
    },
    {
        id: 'listing-3',
        title: 'Comm Array Dish, 3m, pitted',
        category: 'Comm Arrays & Beacons',
        grade: 'Parts Only',
        askPrice: 310,
        qty: 21,
        seller: 'SCRAPWIFE',
        origin: 'navigational-loss auction',
        description:
            'Dish face is pitted from micrometeor exposure, but the feed horn ' +
            'still tests clean. Parts-only — no functional warranty.',
    },
    {
        id: 'listing-4',
        title: 'Hull Plating, 2x2m, micrometeor scarred',
        category: 'Hull Plating & Armor',
        grade: 'Cold-Soak',
        askPrice: 640,
        qty: 40,
        seller: 'TIN_CAN_TRADER',
        origin: 'decommission yard',
        description:
            'Standard 2x2m plate off a decommissioned hull. Scarring is ' +
            'cosmetic; structural integrity holds to spec.',
    },
    {
        id: 'listing-5',
        title: 'Drone Chassis, quad-arm, no core',
        category: 'Drone & Bot Parts',
        grade: 'Reclaimed',
        askPrice: 275,
        qty: 17,
        seller: 'IRON_MAGPIE',
        origin: 'salvage claim #4471',
        description:
            'Quad-arm chassis, no core included. Motors and servos test ' +
            'functional on bench power.',
    },
    {
        id: 'listing-6',
        title: 'Reactor Cell, low-yield, tested stable',
        category: 'Reactor Cores & Cells',
        grade: 'Flight-Worthy',
        askPrice: 9700,
        qty: 2,
        seller: 'GHOSTFREIGHT',
        origin: 'fleet surplus',
        description:
            'Tested stable at low yield. Fleet surplus paperwork included; ' +
            'no output guarantee past six months.',
    },
    {
        id: 'listing-7',
        title: 'Sealed Temporal Displacement Housing, tri-coil intact',
        category: 'Exotic & Unclassified',
        grade: 'Flight-Worthy',
        returnable: false,
        askPrice: FLUX_CAPACITOR_PRICE,
        qty: 1,
        seller: 'UNKNOWN_CONSIGNOR',
        origin: 'temporal anomaly recovery, manifest sealed',
        description:
            'Fabrication origin unknown. Housing reads as a sealed Y-shaped ' +
            'tri-coil flux assembly wrapped around a central displacement core, ' +
            'with time-displacement circuitry bonded directly to the casing. ' +
            'Rated input draw: 1.21 gigawatts, sustained. Output coupling is ' +
            'unlike any registered drive coil — dispersal characteristics only ' +
            'stabilize once the housing exceeds roughly 88 units of relative ' +
            'velocity. A hand-lettered placard is zip-tied to the casing: ' +
            '"DO NOT EXCEED 88 — Doc." No fleet registry has a match for this ' +
            'part. Sold as-is; consignor declined to explain how it was salvaged.',
    },
]
