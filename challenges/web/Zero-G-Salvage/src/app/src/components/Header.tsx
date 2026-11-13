import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import logoUrl from "../assets/zero-g-salvage-logo.svg";
import { formatCredits } from "../util";

const POP_LIFETIME_MS = 1500;

interface CreditPop {
	id: number;
	delta: number;
}

export function Header({ credits }: { credits?: number }) {
	const prevCreditsRef = useRef<number | undefined>(undefined);
	const [pops, setPops] = useState<CreditPop[]>([]);

	useEffect(() => {
		if (credits === undefined) return;
		const prev = prevCreditsRef.current;
		prevCreditsRef.current = credits;
		if (prev === undefined || credits === prev) return;

		const id = Date.now() + Math.random();
		setPops((current) => [...current, { id, delta: credits - prev }]);
		setTimeout(() => {
			setPops((current) => current.filter((pop) => pop.id !== id));
		}, POP_LIFETIME_MS);
	}, [credits]);

	return (
		<header className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/90 backdrop-blur">
			<div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
				<Link to="/" className="flex items-center gap-3">
					<img src={logoUrl} alt="Zero-G Salvage" className="h-10 w-10" />
					<div className="leading-tight">
						<p className="font-semibold tracking-wide">ZERO-G SALVAGE</p>
						<p className="text-xs text-slate-400">
							Materials &amp; Parts Xchange
						</p>
					</div>
				</Link>
				<nav className="hidden items-center gap-6 text-sm text-slate-300 sm:flex">
					<a className="hover:text-white" href="/#markets">
						Markets
					</a>
					<Link className="hover:text-white" to="/listings">
						Listings
					</Link>
					<Link className="hover:text-white" to="/portfolio">
						Portfolio
					</Link>
					<Link className="hover:text-white" to="/disclosures">
						Disclosures
					</Link>
				</nav>
				{credits !== undefined && (
					<span className="relative inline-block rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-center text-sm font-medium tabular-nums text-amber-400">
						{formatCredits(credits)} cr
						{pops.map((pop) => (
							<span
								key={pop.id}
								className={`credit-pop pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 whitespace-nowrap text-sm font-semibold ${
									pop.delta > 0 ? "text-emerald-400" : "text-rose-400"
								}`}
							>
								{pop.delta > 0 ? "+" : "-"}
								{formatCredits(Math.abs(pop.delta))} cr
							</span>
						))}
					</span>
				)}
			</div>
		</header>
	);
}
