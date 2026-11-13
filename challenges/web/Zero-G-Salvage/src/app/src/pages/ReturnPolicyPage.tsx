import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Header } from "../components/Header";
import type { Account } from "../types";
import { requestServer } from "../util";

function ReturnPolicyPage() {
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
					Return &amp; Refund Policy
				</h1>
				<p className="mt-2 text-sm text-slate-400">
					Covers purchases made through User Listings.
				</p>

				<div className="mt-8 space-y-8 text-sm leading-relaxed text-slate-300">
					<section>
						<h2 className="text-base font-semibold text-white">
							General Returns
						</h2>
						<p className="mt-2">
							A listing purchased through User Listings may be returned for a
							full refund of the ask price within 7 days. No restocking fee, no
							questions asked.
						</p>
					</section>

					<section>
						<h2 className="text-base font-semibold text-white">Exclusions</h2>
						<p className="mt-2">
							One-of-a-kind salvage lots and sealed or unclassified artifacts
							are final sale and are not eligible for return once purchased. Any
							listing marked non-returnable in its own description is excluded
							regardless of category.
						</p>
					</section>

					<section>
						<h2 className="text-base font-semibold text-white">
							How to Return
						</h2>
						<p className="mt-2">
							Return an eligible purchase from its card on your{" "}
							<Link
								to="/portfolio"
								className="text-cyan-400 hover:text-cyan-300"
							>
								Portfolio
							</Link>{" "}
							page. Refunds post to your account balance instantly.
						</p>
					</section>
				</div>
			</div>
		</div>
	);
}

export default ReturnPolicyPage;
