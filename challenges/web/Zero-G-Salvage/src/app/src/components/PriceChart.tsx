import type { MouseEvent } from "react";
import { useMemo, useRef, useState } from "react";
import type { PricePoint } from "../types";
import { formatCredits } from "../util";

const WIDTH = 640;
const HEIGHT = 220;
const PADDING_TOP = 16;
const PADDING_BOTTOM = 16;
const PADDING_LEFT = 64;
const PADDING_RIGHT = 16;
const GRIDLINE_COUNT = 4;
const CHART_WIDTH = WIDTH - PADDING_LEFT - PADDING_RIGHT;
const CHART_HEIGHT = HEIGHT - PADDING_TOP - PADDING_BOTTOM;
const TOOLTIP_WIDTH = 120;
const TOOLTIP_HEIGHT = 40;

export function PriceChart({ points }: { points: PricePoint[] }) {
	const svgRef = useRef<SVGSVGElement>(null);
	const [hoverIndex, setHoverIndex] = useState<number | null>(null);

	const prices = points.map((p) => p.price);
	const min = prices.length ? Math.min(...prices) : 0;
	const max = prices.length ? Math.max(...prices) : 0;
	const range = max - min || 1;
	const stepX = CHART_WIDTH / Math.max(points.length - 1, 1);

	const coords = useMemo(
		() =>
			points.map((p, i) => {
				const x = PADDING_LEFT + i * stepX;
				const y =
					PADDING_TOP + CHART_HEIGHT - ((p.price - min) / range) * CHART_HEIGHT;
				return [x, y] as const;
			}),
		[points, stepX, min, range],
	);

	if (points.length === 0) return null;

	const linePath = coords
		.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
		.join(" ");
	const [firstX] = coords[0];
	const [lastX] = coords[coords.length - 1];
	const floorY = PADDING_TOP + CHART_HEIGHT;
	const areaPath = `${linePath} L${lastX.toFixed(1)},${floorY} L${firstX.toFixed(1)},${floorY} Z`;

	const up = points[points.length - 1].price >= points[0].price;
	const stroke = up ? "#34d399" : "#fb7185";
	const fill = up ? "rgba(52,211,153,0.12)" : "rgba(251,113,133,0.12)";

	const gridlines = Array.from({ length: GRIDLINE_COUNT + 1 }, (_, i) => {
		const value = min + (range * i) / GRIDLINE_COUNT;
		const y = floorY - (i / GRIDLINE_COUNT) * CHART_HEIGHT;
		return { value, y };
	});

	function handleMove(e: MouseEvent<SVGSVGElement>) {
		const svg = svgRef.current;
		if (!svg) return;
		const rect = svg.getBoundingClientRect();
		const xUser = ((e.clientX - rect.left) / rect.width) * WIDTH;
		const rawIndex = Math.round((xUser - PADDING_LEFT) / stepX);
		setHoverIndex(Math.min(Math.max(rawIndex, 0), points.length - 1));
	}

	const hovered = hoverIndex !== null ? points[hoverIndex] : null;
	const hoverX = hoverIndex !== null ? coords[hoverIndex][0] : null;
	const hoverY = hoverIndex !== null ? coords[hoverIndex][1] : null;
	const tooltipOnLeft =
		hoverX !== null && hoverX + 12 + TOOLTIP_WIDTH > WIDTH - PADDING_RIGHT;
	const tooltipX =
		hoverX === null
			? 0
			: tooltipOnLeft
				? hoverX - 12 - TOOLTIP_WIDTH
				: hoverX + 12;
	const tooltipY =
		hoverY === null
			? 0
			: Math.min(
					Math.max(hoverY - TOOLTIP_HEIGHT / 2, PADDING_TOP),
					floorY - TOOLTIP_HEIGHT,
				);

	return (
		<svg
			ref={svgRef}
			viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
			className="w-full cursor-crosshair"
			role="img"
			aria-label="Price history chart"
			onMouseMove={handleMove}
			onMouseLeave={() => setHoverIndex(null)}
		>
			{gridlines.map(({ value, y }) => (
				<g key={value}>
					<line
						x1={PADDING_LEFT}
						x2={WIDTH - PADDING_RIGHT}
						y1={y}
						y2={y}
						stroke="rgba(255,255,255,0.08)"
						strokeWidth={1}
					/>
					<text
						x={PADDING_LEFT - 8}
						y={y}
						textAnchor="end"
						dominantBaseline="middle"
						fontSize={10}
						className="fill-slate-500"
					>
						{formatCredits(value)}
					</text>
				</g>
			))}

			<path d={areaPath} fill={fill} stroke="none" />
			<path d={linePath} fill="none" stroke={stroke} strokeWidth={1} />

			{hoverX !== null && hoverY !== null && hovered && (
				<>
					<line
						x1={hoverX}
						x2={hoverX}
						y1={PADDING_TOP}
						y2={floorY}
						stroke="rgba(255,255,255,0.25)"
						strokeWidth={1}
					/>
					<circle
						cx={hoverX}
						cy={hoverY}
						r={3.5}
						fill={stroke}
						stroke="#0f172a"
						strokeWidth={1.5}
					/>
					<foreignObject
						x={tooltipX}
						y={tooltipY}
						width={TOOLTIP_WIDTH}
						height={TOOLTIP_HEIGHT}
					>
						<div className="pointer-events-none rounded-md border border-white/10 bg-slate-950/95 px-2 py-1 text-[11px] leading-tight text-slate-200 shadow-lg">
							<p className="text-slate-400">{hovered.date}</p>
							<p className="font-semibold text-amber-400">
								{formatCredits(hovered.price)} cr
							</p>
						</div>
					</foreignObject>
				</>
			)}
		</svg>
	);
}
