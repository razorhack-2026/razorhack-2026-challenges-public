# Zero-G Salvage

**Category:** Web
**Difficulty:** Medium
**Author:** Lt. Rico Kopernicus

## Description

Zero-G gives every new account on the exchange 5,000 credits to start, and
we've got some Scrap Steel and Salvaged Iron sitting in our hold (40t and 
25t respectively) that the exchange will happily buy from us. The account 
also qualifies for a one-time signup bonus (3,000 credits). A listing on
the exchange — a sealed "temporal anomaly" artifact — is priced at 30,000
credits, out of reach on its own. Two independent, individually-capped bugs
exist on the exchange; neither alone is enough, but both together clear the
price:

| Source | Credits |
|---|---|
| Starting balance | 5,000 |
| Signup voucher | 3,000 |
| Selling the starter holdings (40t STEEL + 25t IRON), less 2% clearing fee | ~10,490 |
| **Subtotal (no bugs)** | **~18,490** |
| + Bulk Order bug only (8,000, credited directly) | ~26,490 (short by ~3,500) |
| + Quote Lock bug only (8,000, realized via a sale, so ~7,800 net) | ~26,300 (short by ~3,700) |
| + both bugs | ~34,300 (clears 30,000 by ~4,300) |

Measured on a live run: single-bug paths reached 26,312 and 26,488; the full
solve reached 34,314. The holdings figure drifts only a few hundred credits
with the live index, far inside those margins.

## Flag

`flag{1_21_g1g4w4tts_0f_pr0f1t}`

## Solution

Full automated solve: `node solution/solve.js http://<host>:8080`.

### Method 1 — Bulk Order Discount Program, negative-quantity exploit (up to 8,000 credits)

`POST /api/trade/bulk-buy` is a volume-discount buy program: orders of 500+ tons
qualify for a per-ton discount that scales with order size. It prices an order as

```text
discountRate = qty >= 500 ? min(BULK_DISCOUNT_MAX_RATE, qty / BULK_DISCOUNT_SCALE) : 0
cost = qty * pricePerTon * (1 - discountRate)
```

The 500-ton minimum and the requirement that `qty` be positive are enforced only by
the trading terminal's UI (`placeBulkOrder()` rejects anything under 500 before
sending) — the API itself only rejects `0` and non-finite values, so the check
has to be bypassed with DevTools, a proxy, or `curl`. Submitting a large negative
`qty` (e.g. `-100000`) makes `cost` negative, so the `cost > credits` guard never
trips and `credits -= cost` *adds* credits instead of spending them.

The server applies the discount only to orders of 500t+, so honest
sub-500 orders are priced at list and can't be flipped back at the index for
profit. The cheapest eligible order (500t IRON, ~70,000 cr) is unaffordable
before the exploit. Honest discount savings also count toward the same weekly
cap, matching the Disclosures wording.

The payout is capped: the server banks the gain up to `BULK_ORDER_PROFIT_CAP`
(8,000), and once that ceiling is reached it flips `bulkOrderLocked` for the
account — every subsequent call to `/api/trade/bulk-buy`, exploit or legitimate,
gets back `429 Too Many Requests` with "Weekly Bulk Order savings limit reached.
Check back next week." (framed in-fiction as an ordinary weekly quota rather than
a fraud flag — see the Disclosures page, which states the 8,000/week figure
outright). One request with a sufficiently large negative `qty` overshoots the
cap and locks the program in a single shot; no grinding required. `solve.js` runs
this against `COPR`, which the account holds none of. The order leaves that
ticker's holdings deeply negative, so aiming it at `STEEL` or `IRON` would block
selling the starter cargo afterwards (the bug itself works identically on any
ticker).

### Method 2 — Quote Lock, client-trusted price (up to 8,000 credits)

`POST /api/quote/lock` lets a trader lock the current price on a quantity for 15
seconds before executing, protecting against index drift during settlement. It
stores `{ ticker, qty, price }` server-side keyed by a `quoteId` and returns all
four fields to the client.

`POST /api/quote/execute` reads `qty` and `ticker` from the stored quote (trusted —
can't be tampered), but computes settlement as `fairCost - cappedGain` where
`fairCost` uses the *locked* price and `cappedGain` is `fairCost` minus whatever
price the client supplies in the request body. Executing with a near-zero price
(e.g. `0.01`) maximizes that gain — but the payout comes out as an
underpriced *lot of goods*, not direct credits, since the trade still settles
for `fairCost - cappedGain`, not the tampered price outright. Realizing the
profit takes one more step: sell the acquired lot straight back at the index
over `POST /api/trade/sell` (less the 2% clearing fee).

Same lockdown pattern as Method 1: the gain is banked up to
`QUOTE_LOCK_PROFIT_CAP` (8,000), and once reached, `quoteLockLocked` flips and
both `/api/quote/lock` and `/api/quote/execute` return `423 Locked` with "Quote
Lock suspended for this account pending anomaly review" from then on. `solve.js`
locks 50 tons of `STEEL` — enough that its fair value (~9,000 credits) clears
the 8,000 cap in one shot while keeping the out-of-pocket cost (`fairCost -
8,000`, roughly 1,000 credits) affordable — executes at `0.01` cr/t, then sells
the 50-ton lot back at the index to pocket the difference. After the ~180 cr
clearing fee on that sale, it nets roughly 7,800.

The gain is only committed to the ledger *after* the credit check passes. Locking
too large a lot (e.g. 1000t, where `fairCost - 8,000` exceeds the balance)
returns `402 Insufficient credits` without tripping the suspension, so the
player can retry with a smaller lot.

### Starter holdings

Sell the 40t STEEL and 25t IRON over `POST /api/trade/sell` (~10,700 cr gross,
~10,490 after the clearing fee). This is ordinary trading, but it's part of the
budget.

### Final step — purchase the artifact

Once combined balance reaches 30,000 credits, `POST
/api/listings/<flux-capacitor-id>/purchase` succeeds and the response includes
the flag, and the listing card itself will show the flag as well.

## Notes

- **In-app hints.** The `/disclosures` page (linked from the footer, header nav,
  the voucher redeem block, and each commodity's trade/bulk-order/quote-lock
  panels) describes both programs in dry, honest disclosure-style copy without
  naming the bugs outright, so a careful reader can identify both surfaces to investigate.
- **Market trading is not a path.** Prices tick with +/-0.1% noise and pull
  back toward a fixed reference, so the whole hour of history spans only about
  1% from low to high. Every sale pays a 2% clearing fee (disclosed on the
  Disclosures page and the trade panel), so no buy-low/sell-high round trip,
  including using Quote Lock's 15s window as a look-ahead, can turn a profit.
  An offline simulation of both strategies never beat the starting balance over
  4 hours. Before this change, with +/-0.6% noise and no fee, a bot reached
  30,000 from zero bugs in ~13 min.
- **Purchase gating is per-session**, not a shared listing `qty` decrement — one
  team solving it doesn't lock another team out on a shared instance.
- **Deployment.** One public port. The `frontend` container is nginx: it serves
  the built SPA and proxies only `/api/*` to `127.0.0.1:3001`: frontend and
  backend share one network namespace (one Fargate task), and the backend
  listens on `127.0.0.1` only, so players can't reach it directly, and its
  source and `FLAG` env var live only in the backend container. Frontend and
  API share one origin, so the
  `SameSite=Lax` session cookie always rides along and there's no CORS. The
  rate limiters key on the session cookie, so they're unaffected by the proxy.
  For local dev, `npm run dev` proxies `/api` to `127.0.0.1:3001` the same way,
  so nothing extra is needed.

## Techniques / Tags

`web`, `business-logic`, `input-validation`, `client-side-trust`, `price-tampering`
