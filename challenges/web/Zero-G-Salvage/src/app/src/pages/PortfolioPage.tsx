import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Header } from "../components/Header";
import { ListingCard } from "../components/ListingCard";
import type { Account, Commodity, Listing, ReturnResult } from "../types";
import {
	formatCredits,
	formatNumber,
	LIVE_UPDATE_INTERVAL_MS,
	postServer,
	requestServer,
} from "../util";

function PortfolioPage() {
	const [account, setAccount] = useState<Account | null>(null);
	const [commodities, setCommodities] = useState<Commodity[]>([]);
	const [listings, setListings] = useState<Listing[]>([]);
	const [pendingId, setPendingId] = useState<string | null>(null);
	const [message, setMessage] = useState<string | null>(null);

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

	useEffect(() => {
		Promise.all([
			requestServer<Account>("/api/account"),
			requestServer<Listing[]>("/api/listings"),
			requestServer<Commodity[]>("/api/commodities"),
		])
			.then(([accountData, listingData, commodityData]) => {
				setAccount(accountData);
				setListings(listingData);
				setCommodities(commodityData);
			})
			.catch(() => {});
	}, []);

	useEffect(() => {
		const id = setInterval(() => {
			requestServer<Commodity[]>("/api/commodities")
				.then(setCommodities)
				.catch(() => {});
		}, LIVE_UPDATE_INTERVAL_MS);
		return () => clearInterval(id);
	}, []);

	function returnItem(item: Listing) {
		setPendingId(item.id);
		setMessage(null);
		postServer<ReturnResult>(`/api/listings/${item.id}/return`)
			.then(() => {
				refreshAccount();
				refreshListings();
			})
			.catch((err: Error) => setMessage(err.message))
			.finally(() => setPendingId(null));
	}

	function switchAccount() {
		if (
			!window.confirm(
				"Start a new trader account? This resets your credits and holdings back to the starting stake.",
			)
		) {
			return;
		}
		postServer("/api/session/reset")
			.then(() => window.location.reload())
			.catch(() => window.alert("Could not start a new account. Try again."));
	}

	const heldCommodities = commodities.filter(
		(c) => (account?.holdings[c.ticker] ?? 0) !== 0,
	);
	const ownedListings = listings.filter((item) => (item.ownedByYou ?? 0) > 0);

	return (
		<div className="min-h-screen bg-slate-950 text-slate-100">
			<Header credits={account?.credits} />

			<div className="mx-auto max-w-6xl px-4 py-10">
				<Link to="/" className="text-sm text-cyan-400 hover:text-cyan-300">
					&larr; Back to Exchange
				</Link>

				<h1 className="mt-4 text-2xl font-bold tracking-tight">Portfolio</h1>
				<p className="mt-2 text-sm text-slate-500">
					Everything your account currently holds, across commodities and User
					Listings purchases.
				</p>

				{message && <p className="mt-4 text-sm text-cyan-300">{message}</p>}

				<h2 className="mt-8 text-xl font-semibold">Commodity Holdings</h2>
				{heldCommodities.length === 0 ? (
					<p className="mt-2 text-sm text-slate-500">No commodity holdings.</p>
				) : (
					<div className="mt-4 overflow-x-auto rounded-lg border border-white/10">
						<table className="w-full min-w-[560px] table-fixed text-left text-sm">
							<colgroup>
								<col className="w-[15%]" />
								<col className="w-[30%]" />
								<col className="w-[15%]" />
								<col className="w-[20%]" />
								<col className="w-[20%]" />
							</colgroup>
							<thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
								<tr>
									<th className="truncate px-4 py-3 font-medium">Ticker</th>
									<th className="truncate px-4 py-3 font-medium">Material</th>
									<th className="truncate px-4 py-3 font-medium">Held (t)</th>
									<th className="truncate px-4 py-3 font-medium">
										Price / Ton
									</th>
									<th className="truncate px-4 py-3 font-medium">Value</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-white/5">
								{heldCommodities.map((c) => {
									const held = account?.holdings[c.ticker] ?? 0;
									return (
										<tr key={c.ticker}>
											<td className="truncate px-4 py-3 font-semibold text-white">
												<Link
													to={`/commodity/${c.ticker}`}
													className="hover:text-cyan-400"
												>
													{c.ticker}
												</Link>
											</td>
											<td className="truncate px-4 py-3 text-slate-300">
												{c.name}
											</td>
											<td className="truncate px-4 py-3 tabular-nums text-slate-400">
												{formatNumber(held.toString())}
											</td>
											<td className="truncate px-4 py-3 tabular-nums text-amber-400">
												{formatCredits(c.pricePerTon)} cr
											</td>
											<td className="truncate px-4 py-3 tabular-nums text-amber-400">
												{formatCredits(held * c.pricePerTon)} cr
											</td>
										</tr>
									);
								})}
							</tbody>
						</table>
					</div>
				)}

				<h2 className="mt-10 text-xl font-semibold">User Listings Owned</h2>
				<p className="mt-1 text-sm text-slate-500">
					<Link
						to="/return-policy"
						className="text-cyan-400 hover:text-cyan-300"
					>
						Return &amp; refund policy
					</Link>{" "}
					applies.
				</p>
				{ownedListings.length === 0 ? (
					<p className="mt-4 text-sm text-slate-500">
						No User Listings purchases yet.
					</p>
				) : (
					<div className="mt-4 grid grid-cols-1 items-start gap-5 sm:grid-cols-2 lg:grid-cols-3">
						{ownedListings.map((item) => (
							<ListingCard
								key={item.id}
								item={item}
								pending={pendingId === item.id}
								onReturn={returnItem}
							/>
						))}
					</div>
				)}

				<h2 className="mt-10 text-xl font-semibold text-rose-400">
					Danger Zone
				</h2>
				<div className="mt-4 flex flex-row items-center rounded-lg border border-rose-500/30 bg-rose-500/5 p-4">
					<div className="flex flex-col w-full">
						<h2 className="text-base font-semibold text-rose-400">
							Reset Trader Account
						</h2>
						<p className="text-sm text-slate-300">
							Starting a new trader account resets your credits and holdings
							back to the starting stake. This can&apos;t be undone.
						</p>
					</div>
					<button
						type="button"
						onClick={switchAccount}
						className="whitespace-nowrap rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-sm font-medium text-rose-300 hover:bg-rose-500/20"
					>
						Start Over
					</button>
				</div>
			</div>
		</div>
	);
}

export default PortfolioPage;
