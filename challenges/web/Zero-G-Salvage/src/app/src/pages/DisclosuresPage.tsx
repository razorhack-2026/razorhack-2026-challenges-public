import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Header } from "../components/Header";
import type { Account } from "../types";
import { requestServer } from "../util";

function DisclosuresPage() {
	const [account, setAccount] = useState<Account | null>(null);

	useEffect(() => {
		requestServer<Account>("/api/account")
			.then(setAccount)
			.catch(() => {});
	}, []);

	return (
		<div className="min-h-screen bg-slate-950 text-slate-100">
			<Header credits={account?.credits} />

			<div className="mx-auto max-w-3xl px-4 py-10">
				<Link to="/" className="text-sm text-cyan-400 hover:text-cyan-300">
					&larr; Back to Exchange
				</Link>

				<h1 className="mt-4 text-2xl font-bold tracking-tight">
					Exchange Disclosures &amp; Terms
				</h1>
				<p className="mt-2 text-sm text-slate-400">
					Published per standard drift-lane trading disclosure practice. Retain
					a copy for your records.
				</p>

				<div className="mt-8 space-y-8 text-sm leading-relaxed text-slate-300">
					<section>
						<h2 className="text-base font-semibold text-white">
							New Trader Signup Bonus — Terms
						</h2>
						<p className="mt-2">
							Every new trading account qualifies for a one-time signup bonus,
							posted to your balance instantly. Only one redemption is honored
							per account.
						</p>
					</section>

					<section>
						<h2 className="text-base font-semibold text-white">
							Bulk Order Discount Program
						</h2>
						<p className="mt-2">
							Orders of 500 tons or more qualify for a volume discount off the
							live index price, scaling with order size up to a maximum rate.
							Order-size eligibility is checked in the trading terminal before
							the request is sent to the exchange. Each trader account can
							receive up to 8,000 credits of bulk discount savings per week —
							once reached, the program is unavailable for the account until the
							following week.
						</p>
					</section>

					<section>
						<h2 className="text-base font-semibold text-white">Quote Lock</h2>
						<p className="mt-2">
							All purchases on the exchange settle through Quote Lock: locking a
							quote fixes your execution price against index drift for up to 15
							seconds. Execution settles at the price recorded on your
							settlement instruction at the time you submit it. A locked
							quote may be canceled any time before it's executed or expires,
							with no obligation to follow through.
						</p>
					</section>

					<section>
						<h2 className="text-base font-semibold text-white">
							Clearing Fees
						</h2>
						<p className="mt-2">
							Sales settle instantly at the live index price through our
							clearing partner, which withholds a 2% clearing fee from the
							proceeds of every sale. Purchases through Quote Lock and the Bulk
							Order Discount Program carry no clearing fee.
						</p>
					</section>

					<section>
						<h2 className="text-base font-semibold text-white">
							Anomaly Review &amp; Settlement Holds
						</h2>
						<p className="mt-2">
							Our automated audit system tracks each account's cumulative
							settlement deviation from published fair value on Quote Lock
							executions. This can occur for a multitude of reasons, including
							natural causes such as solar radiation corrupting data during
							transit.
							If an account's running deviation crosses the internal review
							threshold, Quote Lock is suspended for the account pending manual
							review — other trading programs are unaffected. Review thresholds
							are not published and are subject to change without notice.
						</p>
					</section>

					<section>
						<h2 className="text-base font-semibold text-white">
							Listing Purchases
						</h2>
						<p className="mt-2">
							Purchases made through User Listings are covered by our{" "}
							<Link
								to="/return-policy"
								className="text-cyan-400 hover:text-cyan-300"
							>
								Return &amp; Refund Policy
							</Link>
							.
						</p>
					</section>

					<section>
						<h2 className="text-base font-semibold text-white">General</h2>
						<p className="mt-2">
							Zero-G Salvage is an independent trading post, not a registered
							exchange, and is not affiliated with, endorsed by, or answerable
							to any registered fleet authority. Index prices reflect indicative
							salvage market activity, not guaranteed fleet valuations. All
							goods sold as salvaged, as-is, void in vacuum.
						</p>
					</section>
				</div>
			</div>
		</div>
	);
}

export default DisclosuresPage;
