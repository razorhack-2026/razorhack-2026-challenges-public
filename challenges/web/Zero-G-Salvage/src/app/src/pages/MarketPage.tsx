import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Change } from "../components/Change";
import { Header } from "../components/Header";
import { ListingCard } from "../components/ListingCard";
import type {
	Account,
	Commodity,
	Listing,
	MarketStats,
	PurchaseResult,
	VoucherResult,
} from "../types";
import {
	formatCredits,
	formatMillions,
	formatNumber,
	LIVE_UPDATE_INTERVAL_MS,
	postServer,
	requestServer,
	voucherRedeemedKey,
} from "../util";

const LISTINGS_PREVIEW_COUNT = 3;

function TickerTape({ commodities }: { commodities: Commodity[] }) {
	const items = [...commodities, ...commodities];
	return (
		<div className="overflow-hidden border-b border-white/10 bg-slate-900/60">
			<div className="ticker-track flex w-max gap-8 whitespace-nowrap px-4 py-2 text-xs">
				{items.map((c, i) => (
					<span
						key={`${c.ticker}-${i}`}
						className="flex items-center gap-2 text-slate-300"
					>
						<span className="font-semibold text-white">{c.ticker}</span>
						<span>{formatCredits(c.pricePerTon)} cr/t</span>
						<Change pct={c.changePct} />
					</span>
				))}
			</div>
		</div>
	);
}

function MarketPage() {
	const navigate = useNavigate();
	const [commodities, setCommodities] = useState<Commodity[]>([]);
	const [listings, setListings] = useState<Listing[]>([]);
	const [account, setAccount] = useState<Account | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [query, setQuery] = useState("");
	const [showSuggestions, setShowSuggestions] = useState(false);
	const searchRef = useRef<HTMLDivElement>(null);
	const [voucherMessage, setVoucherMessage] = useState<string | null>(null);
	const [voucherPending, setVoucherPending] = useState(false);
	const [voucherHidden, setVoucherHidden] = useState(false);
	const [sessionId, setSessionId] = useState<string | null>(null);
	const [stats, setStats] = useState<MarketStats | null>(null);
	const [purchasePendingId, setPurchasePendingId] = useState<string | null>(
		null,
	);
	const [purchaseMessage, setPurchaseMessage] = useState<string | null>(null);

	function refreshAccount() {
		requestServer<Account>("/api/account")
			.then(setAccount)
			.catch(() => {});
	}

	function refreshListings() {
		requestServer<Listing[]>("/api/listings")
			.then(setListings)
			.catch(() => {});
	}

	function redeemVoucher() {
		setVoucherPending(true);
		setVoucherMessage(null);
		postServer<VoucherResult>("/api/voucher/redeem")
			.then((result) => {
				setVoucherMessage(
					`Voucher applied: +${formatCredits(result.granted)} cr`,
				);
				if (sessionId) {
					window.localStorage.setItem(voucherRedeemedKey(sessionId), "true");
				}
				setVoucherHidden(true);
				refreshAccount();
			})
			.catch((err: Error) => {
				setVoucherMessage(err.message);
				if (err.message === "Voucher already redeemed") {
					if (sessionId) {
						window.localStorage.setItem(voucherRedeemedKey(sessionId), "true");
					}
					setTimeout(() => setVoucherHidden(true), 3000);
				}
			})
			.finally(() => setVoucherPending(false));
	}

	function purchaseListing(item: Listing) {
		setPurchasePendingId(item.id);
		setPurchaseMessage(null);
		postServer<PurchaseResult>(`/api/listings/${item.id}/purchase`)
			.then((result) => {
				setPurchaseMessage(`Purchased ${result.item}.`);
				refreshAccount();
				refreshListings();
			})
			.catch((err: Error) => setPurchaseMessage(err.message))
			.finally(() => setPurchasePendingId(null));
	}

	useEffect(() => {
		function handleClickOutside(e: MouseEvent) {
			if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
				setShowSuggestions(false);
			}
		}
		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	});

	useEffect(() => {
		Promise.all([
			requestServer<Commodity[]>("/api/commodities"),
			requestServer<Listing[]>("/api/listings"),
			requestServer<Account>("/api/account"),
			requestServer<MarketStats>("/api/stats"),
			requestServer<{ sessionId: string }>("/api/session"),
		])
			.then(([commodityData, listingData, accountData, statsData, session]) => {
				setCommodities(commodityData);
				setListings(listingData);
				setAccount(accountData);
				setStats(statsData);
				setSessionId(session.sessionId);
				setVoucherHidden(
					window.localStorage.getItem(voucherRedeemedKey(session.sessionId)) ===
						"true",
				);
			})
			.catch(() => setError("Unable to reach the exchange server."));
	}, []);

	useEffect(() => {
		const id = setInterval(() => {
			requestServer<Commodity[]>("/api/commodities")
				.then((commodityList) => {
					setCommodities(commodityList);
				})
				.catch(() => {});
			requestServer<MarketStats>("/api/stats")
				.then(setStats)
				.catch(() => {});
		}, LIVE_UPDATE_INTERVAL_MS);
		return () => clearInterval(id);
	}, []);

	const normalizedQuery = query.trim().toLowerCase();
	const matchedCommodities = normalizedQuery
		? commodities
				.filter(
					(c) =>
						c.ticker.toLowerCase().includes(normalizedQuery) ||
						c.name.toLowerCase().includes(normalizedQuery),
				)
				.slice(0, 4)
		: [];
	const matchedListings = normalizedQuery
		? listings
				.filter(
					(item) =>
						item.title.toLowerCase().includes(normalizedQuery) ||
						item.category.toLowerCase().includes(normalizedQuery),
				)
				.slice(0, 4)
		: [];
	const hasMatches =
		matchedCommodities.length > 0 || matchedListings.length > 0;

	return (
		<div className="min-h-screen bg-slate-950 text-slate-100">
			<Header credits={account?.credits} />

			{error && (
				<div className="border-b border-rose-500/30 bg-rose-500/10 px-4 py-2 text-center text-sm text-rose-300">
					{error}
				</div>
			)}

			<TickerTape commodities={commodities} />

			<section className="border-b border-white/10 bg-gradient-to-b from-slate-900 to-slate-950">
				<div className="mx-auto max-w-6xl px-4 py-16 text-center">
					<p className="text-sm font-medium uppercase tracking-widest text-cyan-400">
						Est. 2071 · Fleet-Agnostic Salvage Exchange
					</p>
					<h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
						Trade the Drift.
					</h1>
					<p className="mx-auto mt-4 max-w-xl text-slate-400">
						Live commodity pricing on scrap steel, copper, and reclaimed alloys
						pulled off wrecks and decommission yards — plus a board of
						user-listed devices and electronics, priced by the traders selling
						them. Supply moves the market — no fleet paperwork required.
					</p>
					<div ref={searchRef} className="relative mx-auto mt-8 max-w-lg">
						<form className="flex gap-2" onSubmit={(e) => e.preventDefault()}>
							<input
								type="text"
								value={query}
								onChange={(e) => {
									setQuery(e.target.value);
									setShowSuggestions(true);
								}}
								onFocus={() => setShowSuggestions(true)}
								placeholder="Search by ticker, material, or part..."
								className="w-full rounded-md border border-white/10 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none"
							/>
						</form>

						{showSuggestions && normalizedQuery && (
							<div className="absolute inset-x-0 top-full z-20 mt-2 overflow-hidden rounded-md border border-white/10 bg-slate-900 text-left shadow-xl">
								{hasMatches ? (
									<>
										{matchedCommodities.length > 0 && (
											<div className="pb-2">
												<div className="flex justify-between">
													<p className="px-4 pt-3 pb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
														Commodities
													</p>
													<p className="px-4 pt-3 pb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
														Price / Ton
													</p>
												</div>
												{matchedCommodities.map((c) => (
													<Link
														key={c.ticker}
														to={`/commodity/${c.ticker}`}
														onClick={() => setShowSuggestions(false)}
														className="flex items-center justify-between gap-3 px-4 py-2 text-sm hover:bg-slate-800"
													>
														<span>
															<span className="font-semibold text-white">
																{c.ticker}
															</span>{" "}
															<span className="text-slate-400">{c.name}</span>
														</span>
														<span className="text-amber-400">
															{formatCredits(c.pricePerTon)} cr
														</span>
													</Link>
												))}
											</div>
										)}
										{matchedListings.length > 0 && (
											<div
												className={`pb-2 ${matchedCommodities.length > 0 ? "border-t border-white/10" : ""}`}
											>
												<div className="flex justify-between">
													<p className="px-4 pt-3 pb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
														Listings
													</p>
													<p className="px-4 pt-3 pb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
														Price
													</p>
												</div>
												{matchedListings.map((item) => (
													<Link
														key={item.id}
														to="/listings"
														onClick={() => setShowSuggestions(false)}
														className="flex items-center justify-between gap-3 px-4 py-2 text-sm hover:bg-slate-800"
													>
														<span className="text-white">{item.title}</span>
														<span className="text-amber-400">
															{formatCredits(item.askPrice)} cr
														</span>
													</Link>
												))}
											</div>
										)}
									</>
								) : (
									<p className="px-4 py-3 text-sm text-slate-500">
										No matches found.
									</p>
								)}
							</div>
						)}
					</div>
					<p className="mt-6 text-xs tabular-nums text-slate-500">
						{stats &&
							`${formatNumber(stats.tonsCleared.toString())} tons cleared today
							· ${formatNumber(stats.verifiedHaulers.toString())} verified haulers
							· 24h volume ${formatMillions(stats.volumeCr)} cr`}
					</p>

					{!voucherHidden && (
						<>
							<div className="mx-auto mt-6 flex max-w-lg flex-col items-center gap-2 rounded-md border border-white/10 bg-slate-900/60 p-4 sm:flex-row sm:justify-between">
								<p className="text-sm text-slate-300">
									New trader? Redeem your signup voucher for exchange credit.
								</p>
								<button
									type="button"
									disabled={voucherPending}
									onClick={redeemVoucher}
									className="whitespace-nowrap rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-sm font-medium text-cyan-300 hover:bg-cyan-500/20 disabled:opacity-50"
								>
									{voucherPending ? "Redeeming…" : "Redeem Voucher"}
								</button>
							</div>
							{voucherMessage && (
								<p className="mt-2 text-sm text-slate-400">{voucherMessage}</p>
							)}
							<p className="mt-2 text-xs text-slate-500">
								<Link
									to="/disclosures"
									className="text-cyan-400 hover:text-cyan-300"
								>
									Signup bonus terms apply
								</Link>
							</p>
						</>
					)}
				</div>
			</section>

			<section className="border-b border-white/10">
				<div className="mx-auto grid max-w-6xl grid-cols-2 gap-4 px-4 py-8 text-center text-sm text-slate-300 sm:grid-cols-4">
					<div>
						<p className="font-semibold text-white">Live Pricing</p>
						<p className="mt-1 text-xs text-slate-500">
							Index prices update on every fill
						</p>
					</div>
					<div>
						<p className="font-semibold text-white">Escrow Settlement</p>
						<p className="mt-1 text-xs text-slate-500">
							Funds clear when the crate is signed for
						</p>
					</div>
					<div>
						<p className="font-semibold text-white">Salvage Rights Verified</p>
						<p className="mt-1 text-xs text-slate-500">
							Serials checked against the loss registry
						</p>
					</div>
					<div>
						<p className="font-semibold text-white">Any Drift Lane</p>
						<p className="mt-1 text-xs text-slate-500">
							Clearing network spans the outer lanes
						</p>
					</div>
				</div>
			</section>

			<section id="markets" className="mx-auto max-w-6xl px-4 py-14">
				<h2 className="text-xl font-semibold">Commodity Exchange</h2>
				<p className="mt-1 text-sm text-slate-500">
					Bulk salvage materials, priced live by the ton. Select a ticker for
					its price history.
				</p>
				<div className="mt-6 overflow-x-auto rounded-lg border border-white/10">
					<table className="w-full min-w-[760px] table-fixed text-left text-sm">
						<colgroup>
							<col className={account ? "w-[10%]" : "w-[12%]"} />
							<col className={account ? "w-[22%]" : "w-[30%]"} />
							<col className={account ? "w-[14%]" : "w-[18%]"} />
							<col className={account ? "w-[12%]" : "w-[14%]"} />
							<col className={account ? "w-[18%]" : "w-[26%]"} />
							{account && (
								<>
									<col className="w-[12%]" />
									<col className="w-[12%]" />
								</>
							)}
						</colgroup>
						<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
							<tr>
								<th className="truncate px-4 py-3 font-medium">Ticker</th>
								<th className="truncate px-4 py-3 font-medium">Material</th>
								<th className="truncate px-4 py-3 font-medium">Price / Ton</th>
								<th className="truncate px-4 py-3 font-medium">24h Chg</th>
								<th className="truncate px-4 py-3 font-medium">
									24h Volume (t)
								</th>
								{account && (
									<>
										<th className="truncate px-4 py-3 font-medium">Held (t)</th>
										<th className="truncate px-4 py-3 font-medium">Value</th>
									</>
								)}
							</tr>
						</thead>
						<tbody className="divide-y divide-white/5">
							{commodities.map((c) => (
								<tr
									key={c.ticker}
									onClick={() => navigate(`/commodity/${c.ticker}`)}
									className="cursor-pointer hover:bg-slate-900/40"
								>
									<td className="truncate px-4 py-3 font-semibold text-white">
										<Link
											to={`/commodity/${c.ticker}`}
											className="hover:text-cyan-400"
											onClick={(e) => e.stopPropagation()}
										>
											{c.ticker}
										</Link>
									</td>
									<td className="truncate px-4 py-3 text-slate-300">
										{c.name}
									</td>
									<td className="truncate px-4 py-3 tabular-nums text-amber-400">
										{formatCredits(c.pricePerTon)} cr
									</td>
									<td className="truncate px-4 py-3 tabular-nums">
										<Change pct={c.changePct} />
									</td>
									<td className="truncate px-4 py-3 tabular-nums text-slate-400">
										{formatNumber(c.volumeTons.toString())}
									</td>
									{account && (
										<>
											<td className="truncate px-4 py-3 tabular-nums text-slate-400">
												{formatNumber(
													(account.holdings[c.ticker] ?? 0).toString(),
												)}
											</td>
											<td className="truncate px-4 py-3 tabular-nums text-amber-400">
												{formatCredits(
													(account.holdings[c.ticker] ?? 0) * c.pricePerTon,
												)}{" "}
												cr
											</td>
										</>
									)}
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</section>

			<section id="listings" className="mx-auto max-w-6xl px-4 py-14">
				<div className="flex items-baseline justify-between">
					<h2 className="text-xl font-semibold">User Listings</h2>
					<Link
						to="/listings"
						className="text-sm text-cyan-400 hover:text-cyan-300"
					>
						View all listings
					</Link>
				</div>
				<p className="mt-1 text-sm text-slate-500">
					Items listed and priced by the traders selling them.
				</p>
				{purchaseMessage && (
					<p className="mt-4 text-sm text-cyan-300">{purchaseMessage}</p>
				)}
				<div className="mt-6 grid grid-cols-1 items-start gap-5 sm:grid-cols-2 lg:grid-cols-3">
					{listings.slice(0, LISTINGS_PREVIEW_COUNT).map((item) => (
						<ListingCard
							key={item.id}
							item={item}
							credits={account?.credits}
							pending={purchasePendingId === item.id}
							onPurchase={purchaseListing}
						/>
					))}
				</div>
			</section>

			<section
				id="how-it-works"
				className="border-y border-white/10 bg-slate-900/40"
			>
				<div className="mx-auto max-w-6xl px-4 py-14">
					<h2 className="text-xl font-semibold">How Trading Works</h2>
					<div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-3">
						<div>
							<p className="text-sm font-semibold text-cyan-400">
								01 · Claim &amp; Assay
							</p>
							<p className="mt-2 text-sm text-slate-400">
								Stake a salvage claim on a wreck or lot, then get it graded for
								the exchange.
							</p>
						</div>
						<div>
							<p className="text-sm font-semibold text-cyan-400">
								02 · List on the Exchange
							</p>
							<p className="mt-2 text-sm text-slate-400">
								Set an ask price or send it to auction; serials are checked
								against the loss registry.
							</p>
						</div>
						<div>
							<p className="text-sm font-semibold text-cyan-400">
								03 · Settle via Drift Lane
							</p>
							<p className="mt-2 text-sm text-slate-400">
								Courier network handles the drop; escrow clears once the crate
								is signed for.
							</p>
						</div>
					</div>
				</div>
			</section>

			<footer className="mx-auto max-w-6xl px-4 py-10 text-xs text-slate-500">
				<p>
					Zero-G Salvage is an independent trading post, not a registered
					exchange. It is not affiliated with, endorsed by, or answerable to any
					registered fleet authority. Index prices reflect indicative salvage
					market activity, not guaranteed fleet valuations. All goods sold as
					salvaged, as-is, void in vacuum.
				</p>
				<p className="mt-4">
					<Link to="/disclosures" className="text-cyan-400 hover:text-cyan-300">
						Full trading disclosures &amp; settlement terms
					</Link>
					{" · "}
					<Link
						to="/return-policy"
						className="text-cyan-400 hover:text-cyan-300"
					>
						Return &amp; refund policy
					</Link>
				</p>
				<p className="mt-4">&copy; 2074 Zero-G Salvage Registry</p>
			</footer>
		</div>
	);
}

export default MarketPage;
