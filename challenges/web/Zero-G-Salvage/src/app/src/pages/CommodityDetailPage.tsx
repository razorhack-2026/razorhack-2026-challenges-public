import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Change } from "../components/Change";
import { Header } from "../components/Header";
import { PriceChart } from "../components/PriceChart";
import type {
	Account,
	Commodity,
	PricePoint,
	Quote,
	TradeResult,
} from "../types";
import {
	formatCredits,
	formatNumber,
	LIVE_UPDATE_INTERVAL_MS,
	postServer,
	requestServer,
} from "../util";

const QUOTE_COUNTDOWN_TICK_MS = 250;
const BULK_ORDER_MIN_QTY = 500;
const SELL_CLEARING_FEE_PCT = 2;

function CommodityDetailPage() {
	const { ticker = "" } = useParams();
	const upperTicker = ticker.toUpperCase();
	const [commodities, setCommodities] = useState<Commodity[]>([]);
	const [history, setHistory] = useState<PricePoint[]>([]);
	const [account, setAccount] = useState<Account | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);
	const [qtyInput, setQtyInput] = useState("1");
	const [tradePending, setTradePending] = useState(false);
	const [tradeMessage, setTradeMessage] = useState<string | null>(null);

	const [bulkQtyInput, setBulkQtyInput] = useState("500");
	const [bulkPending, setBulkPending] = useState(false);
	const [bulkMessage, setBulkMessage] = useState<string | null>(null);

	const [quote, setQuote] = useState<Quote | null>(null);
	const [quotePending, setQuotePending] = useState(false);
	const [quoteMessage, setQuoteMessage] = useState<string | null>(null);
	const [msRemaining, setMsRemaining] = useState(0);

	function refreshAccount() {
		requestServer<Account>("/api/account")
			.then(setAccount)
			.catch(() => {});
	}

	function sell() {
		const qty = Number(qtyInput);
		if (!(qty > 0)) {
			setTradeMessage("Enter a quantity greater than zero.");
			return;
		}
		setTradePending(true);
		setTradeMessage(null);
		postServer<TradeResult>("/api/trade/sell", { ticker: upperTicker, qty })
			.then((result) => {
				setTradeMessage(
					`Sold ${formatNumber(qty.toString())} t for ${formatCredits(result.proceeds ?? 0)} cr (after ${formatCredits(result.fee ?? 0)} cr clearing fee)`,
				);
				refreshAccount();
			})
			.catch((err: Error) => setTradeMessage(err.message))
			.finally(() => setTradePending(false));
	}

	function placeBulkOrder() {
		const qty = Number(bulkQtyInput);
		if (!Number.isFinite(qty) || qty < BULK_ORDER_MIN_QTY) {
			setBulkMessage(
				`Bulk orders require a minimum of ${formatNumber(BULK_ORDER_MIN_QTY.toString())} tons.`,
			);
			return;
		}
		setBulkPending(true);
		setBulkMessage(null);
		postServer<TradeResult>("/api/trade/bulk-buy", { ticker: upperTicker, qty })
			.then((result) => {
				setBulkMessage(
					`Bulk order filled: ${formatNumber(qty.toString())} t for ${formatCredits(result.cost ?? 0)} cr`,
				);
				refreshAccount();
			})
			.catch((err: Error) => setBulkMessage(err.message))
			.finally(() => setBulkPending(false));
	}

	function lockQuote() {
		const qty = Number(qtyInput);
		if (!(qty > 0)) {
			setQuoteMessage("Enter a quantity greater than zero.");
			return;
		}
		setQuotePending(true);
		setQuoteMessage(null);
		postServer<Quote>("/api/quote/lock", { ticker: upperTicker, qty })
			.then((result) => {
				setQuote(result);
				setQuoteMessage(
					`Locked ${formatNumber(qty.toString())} t at ${formatCredits(result.price)} cr/t`,
				);
			})
			.catch((err: Error) => setQuoteMessage(err.message))
			.finally(() => setQuotePending(false));
	}

	function executeQuote() {
		if (!quote) return;
		setQuotePending(true);
		setQuoteMessage(null);
		postServer<TradeResult>("/api/quote/execute", {
			quoteId: quote.quoteId,
			price: quote.price,
		})
			.then((result) => {
				setQuoteMessage(
					`Executed locked trade for ${formatCredits(result.cost ?? 0)} cr`,
				);
				setQuote(null);
				refreshAccount();
			})
			.catch((err: Error) => setQuoteMessage(err.message))
			.finally(() => setQuotePending(false));
	}

	function cancelQuote() {
		if (!quote) return;
		setQuotePending(true);
		setQuoteMessage(null);
		postServer<{ canceled: boolean }>("/api/quote/cancel", {
			quoteId: quote.quoteId,
		})
			.then(() => {
				setQuote(null);
				setQuoteMessage("Locked quote canceled.");
			})
			.catch((err: Error) => setQuoteMessage(err.message))
			.finally(() => setQuotePending(false));
	}

	useEffect(() => {
		if (!quote) return;
		const id = setInterval(() => {
			setMsRemaining(Math.max(0, quote.expiresAt - Date.now()));
		}, QUOTE_COUNTDOWN_TICK_MS);
		setMsRemaining(Math.max(0, quote.expiresAt - Date.now()));
		return () => clearInterval(id);
	}, [quote]);

	const quoteExpired = quote !== null && msRemaining <= 0;

	useEffect(() => {
		setLoading(true);
		setError(null);
		setHistory([]);

		Promise.all([
			requestServer<Commodity[]>("/api/commodities"),
			requestServer<PricePoint[]>(`/api/commodities/${ticker}/history`),
			requestServer<Account>("/api/account"),
		])
			.then(([commodityList, historyData, accountData]) => {
				setCommodities(commodityList);
				setHistory(historyData);
				setAccount(accountData);
			})
			.catch(() => setError("Unable to load ticker details."))
			.finally(() => setLoading(false));
	}, [ticker]);

	useEffect(() => {
		const id = setInterval(() => {
			Promise.all([
				requestServer<Commodity[]>("/api/commodities"),
				requestServer<PricePoint[]>(`/api/commodities/${ticker}/history`),
			])
				.then(([commodityList, historyData]) => {
					setCommodities(commodityList);
					setHistory(historyData);
				})
				.catch(() => {});
		}, LIVE_UPDATE_INTERVAL_MS);
		return () => clearInterval(id);
	}, [ticker]);

	const commodity = commodities.find((c) => c.ticker === upperTicker) ?? null;
	const held = account?.holdings[upperTicker] ?? 0;

	const currentIndex = commodities.findIndex((c) => c.ticker === upperTicker);
	const otherTickers =
		currentIndex === -1
			? []
			: Array.from(
					{ length: Math.min(3, commodities.length - 1) },
					(_, i) => commodities[(currentIndex + i + 1) % commodities.length],
				);

	return (
		<div className="min-h-screen bg-slate-950 text-slate-100">
			<Header credits={account?.credits} />

			{error && (
				<div className="border-b border-rose-500/30 bg-rose-500/10 px-4 py-2 text-center text-sm text-rose-300">
					{error}
				</div>
			)}

			<div className="mx-auto max-w-6xl px-4 py-10">
				<Link to="/" className="text-sm text-cyan-400 hover:text-cyan-300">
					&larr; Back to Exchange
				</Link>

				{commodity && (
					<>
						<div className="mt-4 flex flex-wrap items-end justify-between gap-4">
							<div>
								<p className="text-sm font-medium uppercase tracking-widest text-cyan-400">
									{commodity.ticker}
								</p>
								<h1 className="mt-1 text-3xl font-bold tracking-tight">
									{commodity.name}
								</h1>
							</div>
							<div className="text-right">
								<p className="text-2xl font-semibold text-amber-400">
									{formatCredits(commodity.pricePerTon)} cr/t
								</p>
								<Change pct={commodity.changePct} />
							</div>
						</div>

						<div className="mt-8 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_200px]">
							<div className="rounded-lg border border-white/10 bg-slate-900/60 p-4">
								<p className="text-sm font-medium text-slate-300">
									Price History
								</p>
								<div className="mt-4">
									<PriceChart points={history} />
								</div>
							</div>

							{otherTickers.length > 0 && (
								<div className="flex flex-col gap-3">
									{otherTickers.map((c) => (
										<Link
											key={c.ticker}
											to={`/commodity/${c.ticker}`}
											className="flex flex-1 flex-col justify-center gap-1 rounded-lg border border-white/10 bg-slate-900/60 p-3 transition hover:border-cyan-500/40 hover:bg-slate-900"
										>
											<span className="text-sm font-semibold text-white">
												{c.ticker}
											</span>
											<span className="text-base font-semibold text-amber-400">
												{formatCredits(c.pricePerTon)} cr/t
											</span>
											<Change pct={c.changePct} />
										</Link>
									))}
								</div>
							)}
						</div>

						<div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
							<div className="rounded-lg border border-white/10 bg-slate-900/60 p-4">
								<p className="text-xs uppercase tracking-wide text-slate-500">
									24h Volume
								</p>
								<p className="mt-1 text-lg font-semibold text-white">
									{formatNumber(commodity.volumeTons.toString())} t
								</p>
							</div>
							{account && (
								<>
									<div className="rounded-lg border border-white/10 bg-slate-900/60 p-4">
										<p className="text-xs uppercase tracking-wide text-slate-500">
											Held
										</p>
										<p className="mt-1 text-lg font-semibold text-white">
											{formatNumber(held.toString())} t
										</p>
									</div>
									<div className="rounded-lg border border-white/10 bg-slate-900/60 p-4">
										<p className="text-xs uppercase tracking-wide text-slate-500">
											Value
										</p>
										<p className="mt-1 text-lg font-semibold text-amber-400">
											{formatCredits(held * commodity.pricePerTon)} cr
										</p>
									</div>
								</>
							)}
						</div>

						{account && (
							<div className="mt-6 rounded-lg border border-white/10 bg-slate-900/60 p-4">
								<p className="text-sm font-medium text-slate-300">
									Trade {commodity.ticker}
								</p>
								<p className="mt-1 text-xs text-slate-500">
									Buying locks the current price for 15 seconds before executing, so
									market drift during settlement doesn't work against you.
									Selling settles instantly at the live index price, less a{" "}
									{SELL_CLEARING_FEE_PCT}% clearing fee.
								</p>
								<div className="mt-3 flex flex-wrap items-center gap-2">
									<input
										type="number"
										min="0"
										step="0.1"
										value={qtyInput}
										onChange={(e) => setQtyInput(e.target.value)}
										className="w-32 rounded-md border border-white/10 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 focus:border-cyan-500 focus:outline-none"
									/>
									<span className="text-sm text-slate-500">tons</span>
									<button
										type="button"
										disabled={tradePending}
										onClick={sell}
										className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-sm font-medium text-amber-300 hover:bg-amber-500/20 disabled:opacity-50"
									>
										Sell
									</button>
									{!quote || quoteExpired ? (
										<button
											type="button"
											disabled={quotePending}
											onClick={lockQuote}
											className="rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-sm font-medium text-cyan-300 hover:bg-cyan-500/20 disabled:opacity-50"
										>
											Lock Price to Buy
										</button>
									) : (
										<>
											<button
												type="button"
												disabled={quotePending}
												onClick={executeQuote}
												className="rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-sm font-medium text-cyan-300 hover:bg-cyan-500/20 disabled:opacity-50"
											>
												Execute Locked Buy
											</button>
											<button
												type="button"
												disabled={quotePending}
												onClick={cancelQuote}
												className="rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-sm font-medium text-rose-300 hover:bg-rose-500/20 disabled:opacity-50"
											>
												Cancel
											</button>
										</>
									)}
								</div>
								{quote && !quoteExpired && (
									<p className="mt-2 text-sm text-slate-300">
										Locked {formatNumber(quote.qty.toString())} t at{" "}
										{formatCredits(quote.price)} cr/t &middot;{" "}
										{Math.ceil(msRemaining / 1000)}s left
									</p>
								)}
								{quoteExpired && (
									<p className="mt-2 text-sm text-slate-500">
										Quote expired — lock again.
									</p>
								)}
								{tradeMessage && (
									<p className="mt-2 text-sm text-slate-400">{tradeMessage}</p>
								)}
								{quoteMessage && (
									<p className="mt-2 text-sm text-slate-400">{quoteMessage}</p>
								)}
								<p className="mt-2 text-xs text-slate-500">
									<Link
										to="/disclosures"
										className="text-cyan-400 hover:text-cyan-300"
									>
										Settlement &amp; clearing terms apply
									</Link>
								</p>
							</div>
						)}

						{account && (
							<div className="mt-6 rounded-lg border border-white/10 bg-slate-900/60 p-4">
								<p className="text-sm font-medium text-slate-300">
									Bulk Order Discount Program
								</p>
								<p className="mt-1 text-xs text-slate-500">
									Orders of {formatNumber(BULK_ORDER_MIN_QTY.toString())}+ tons
									qualify for a volume discount off the live index price.
								</p>
								<div className="mt-3 flex flex-wrap items-center gap-2">
									<input
										type="number"
										min={BULK_ORDER_MIN_QTY}
										step="1"
										value={bulkQtyInput}
										onChange={(e) => setBulkQtyInput(e.target.value)}
										className="w-32 rounded-md border border-white/10 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 focus:border-cyan-500 focus:outline-none"
									/>
									<span className="text-sm text-slate-500">tons</span>
									<button
										type="button"
										disabled={bulkPending}
										onClick={placeBulkOrder}
										className="rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-sm font-medium text-cyan-300 hover:bg-cyan-500/20 disabled:opacity-50"
									>
										Place Bulk Order
									</button>
								</div>
								{bulkMessage && (
									<p className="mt-2 text-sm text-slate-400">{bulkMessage}</p>
								)}
								<p className="mt-2 text-xs text-slate-500">
									<Link
										to="/disclosures"
										className="text-cyan-400 hover:text-cyan-300"
									>
										Settlement &amp; clearing terms apply
									</Link>
								</p>
							</div>
						)}
					</>
				)}

				{!commodity && !loading && !error && (
					<p className="mt-6 text-sm text-slate-400">
						No ticker found for &ldquo;{ticker}&rdquo;.
					</p>
				)}
				{loading && (
					<p className="mt-6 text-sm text-slate-400">Loading ticker details…</p>
				)}
			</div>
		</div>
	);
}

export default CommodityDetailPage;
