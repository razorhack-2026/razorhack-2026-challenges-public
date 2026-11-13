import type { Grade, Listing } from "../types";
import { formatCredits, formatNumber } from "../util";

export const gradeColor: Record<Grade, string> = {
	"Flight-Worthy": "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
	Reclaimed: "bg-cyan-500/15 text-cyan-300 ring-cyan-500/30",
	"Cold-Soak": "bg-amber-500/15 text-amber-300 ring-amber-500/30",
	"Parts Only": "bg-slate-500/15 text-slate-300 ring-slate-500/30",
};

export function ListingCard({
	item,
	credits,
	pending,
	onPurchase,
	onReturn,
}: {
	item: Listing;
	credits?: number;
	pending: boolean;
	onPurchase?: (item: Listing) => void;
	onReturn?: (item: Listing) => void;
}) {
	const owned = item.ownedByYou ?? 0;

	return (
		<div className="flex flex-col rounded-lg border border-white/10 bg-slate-900/60 p-4">
			<div className="flex items-start justify-between gap-2">
				<p className="font-medium text-white">{item.title}</p>
				<span
					className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${gradeColor[item.grade]}`}
				>
					{item.grade}
				</span>
			</div>
			<p className="mt-1 text-xs text-slate-500">{item.category}</p>
			{item.description && (
				<p className="mt-2 text-xs text-slate-400">{item.description}</p>
			)}
			<div className="mt-4 flex items-center justify-between text-sm">
				<span className="font-semibold text-amber-400">
					{formatCredits(item.askPrice)} cr
				</span>
				<span className="text-xs text-slate-500">
					{onReturn
						? `${formatNumber(owned.toString())} owned`
						: `${owned > 0 ? `${formatNumber(owned.toString())} owned · ` : ""}${formatNumber(item.qty.toString())} in stock`}
				</span>
			</div>
			<div className="mt-2 text-xs text-slate-500">
				{item.seller} · {item.origin}
			</div>
			{item.flag && (
				<div className="mt-3 break-all rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 font-mono text-xs text-emerald-300">
					{item.flag}
				</div>
			)}
			{(onPurchase || onReturn) && (
				<div className="mt-4 flex gap-2">
					{onPurchase && credits !== undefined && (
						<button
							type="button"
							disabled={item.qty <= 0 || credits < item.askPrice || pending}
							onClick={() => onPurchase(item)}
							className="flex-1 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-sm font-medium text-emerald-300 hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-transparent disabled:text-slate-600"
						>
							{item.qty <= 0 ? "Sold Out" : pending ? "Working…" : "Purchase"}
						</button>
					)}
					{onReturn && owned > 0 && (
						<button
							type="button"
							disabled={pending || item.returnable === false}
							title={
								item.returnable === false
									? "This item is final sale and not eligible for return."
									: undefined
							}
							onClick={() => onReturn(item)}
							className="flex-1 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-sm font-medium text-rose-300 hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-transparent disabled:text-slate-600"
						>
							{item.returnable === false
								? "Final Sale"
								: pending
									? "Working…"
									: "Return"}
						</button>
					)}
				</div>
			)}
		</div>
	);
}
