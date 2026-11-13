export function Change({ pct }: { pct: number }) {
	const up = pct >= 0;
	return (
		<span className={`font-medium ${up ? "text-emerald-400" : "text-rose-400"}`}>
			{up ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}%
		</span>
	);
}
