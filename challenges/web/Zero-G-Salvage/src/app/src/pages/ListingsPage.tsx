import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Header } from "../components/Header";
import { ListingCard } from "../components/ListingCard";
import type { Account, Listing, PurchaseResult } from "../types";
import { postServer, requestServer } from "../util";

function ListingsPage() {
	const [listings, setListings] = useState<Listing[]>([]);
	const [account, setAccount] = useState<Account | null>(null);
	const [pendingId, setPendingId] = useState<string | null>(null);
	const [message, setMessage] = useState<string | null>(null);

	const refreshAccount = useCallback(() => {
		requestServer<Account>("/api/account")
			.then(setAccount)
			.catch(() => {});
	}, []);

	const refreshListings = useCallback(() => {
		requestServer<Listing[]>("/api/listings")
			.then(setListings)
			.catch(() => {});
	}, []);

	useEffect(() => {
		refreshListings();
		refreshAccount();
	}, [refreshListings, refreshAccount]);

	function purchase(item: Listing) {
		setPendingId(item.id);
		setMessage(null);
		postServer<PurchaseResult>(`/api/listings/${item.id}/purchase`)
			.then((result) => {
				setMessage(`Purchased ${result.item}.`);
				refreshAccount();
				refreshListings();
			})
			.catch((err: Error) => setMessage(err.message))
			.finally(() => setPendingId(null));
	}

	return (
		<div className="min-h-screen bg-slate-950 text-slate-100">
			<Header credits={account?.credits} />

			<div className="mx-auto max-w-6xl px-4 py-10">
				<Link to="/" className="text-sm text-cyan-400 hover:text-cyan-300">
					&larr; Back to Exchange
				</Link>

				<h1 className="mt-4 text-2xl font-bold tracking-tight">
					User Listings
				</h1>
				<p className="mt-2 text-sm text-slate-500">
					Items listed and priced by the traders selling them.{" "}
					<Link
						to="/return-policy"
						className="text-cyan-400 hover:text-cyan-300"
					>
						Return &amp; refund policy applies.
					</Link>{" "}
					— manage owned items and returns from your{" "}
					<Link to="/portfolio" className="text-cyan-400 hover:text-cyan-300">
						Portfolio
					</Link>
					.
				</p>

				{message && <p className="mt-4 text-sm text-cyan-300">{message}</p>}

				<div className="mt-6 grid grid-cols-1 items-start gap-5 sm:grid-cols-2 lg:grid-cols-3">
					{listings.map((item) => (
						<ListingCard
							key={item.id}
							item={item}
							credits={account?.credits}
							pending={pendingId === item.id}
							onPurchase={purchase}
						/>
					))}
				</div>
			</div>
		</div>
	);
}

export default ListingsPage;
