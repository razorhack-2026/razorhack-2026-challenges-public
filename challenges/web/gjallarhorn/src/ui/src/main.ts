import "./styles.css";

type GNode = {
	id: string;
	name: string;
	region: string;
	x: number;
	y: number;
	status?: string;
	note?: string;
};
function need<T>(v: T | null | undefined): T {
	if (v === null || v === undefined) throw new Error("missing element");
	return v;
}

type Graph = {
	regions: string[];
	nodes: GNode[];
	links: [string, string][];
	relay: [string, string][];
	core: { x: number; y: number; strokes: number[][][] };
};
type Frame = {
	sender: string;
	origin: string;
	hops: string[];
	trace: string | null;
	note: string | null;
	raw: string | null;
	sig: string;
	expectedSig: string;
};
type Msg = {
	id: string;
	kind: string;
	label: string;
	text: string;
	ts: string;
	frame: Frame;
	cutAt?: number;
	overwrites?: string;
};
type NState = "normal" | "amber" | "dark" | "red" | "green";

const $ = <T extends HTMLElement>(id: string) =>
	document.getElementById(id) as T;
const SPECIAL = new Set(["ODINS_EYES", "HUGINN", "MUNINN"]);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const esc = (s: unknown) =>
	String(s ?? "").replace(/[&<>"]/g, (c) =>
		need({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]),
	);

let graph: Graph, chat: Msg[];
const byId = new Map<string, GNode>();
const adj = new Map<string, string[]>();
const radj = new Map<string, string[]>(); // relay mesh: where HATI's signal travels
const selected = new Set<string>();
const nstate = new Map<string, NState>();
let focus: string | null = null;
let busy = false;
let solved = false; // set once the purge is right: the horn stays locked
let cooldownUntil = 0;
let banner = "";
let fx: "glitch" | "static" | null = null;
const COOLDOWN_MS = 15000;
const noise = document.createElement("canvas");
noise.width = 160;
noise.height = 100;
const nctx = need(noise.getContext("2d"));
const nimg = nctx.createImageData(noise.width, noise.height);

// radio-wave glitch: displaced bands and colour fringes
function drawGlitch() {
	const dpr = window.devicePixelRatio || 1;
	ctx.save();
	ctx.setTransform(1, 0, 0, 1, 0, 0);
	const bands = 4 + Math.floor(Math.random() * 5);
	for (let i = 0; i < bands; i++) {
		const y = Math.floor(Math.random() * cv.height),
			h = Math.max(2, Math.floor(Math.random() * 28 * dpr));
		const dx = Math.round((Math.random() - 0.5) * 70 * dpr);
		ctx.drawImage(cv, 0, y, cv.width, h, dx, y, cv.width, h);
	}
	ctx.restore();
	for (let i = 0; i < 3; i++) {
		ctx.fillStyle =
			Math.random() < 0.5 ? "rgba(255,40,80,0.10)" : "rgba(40,220,255,0.10)";
		ctx.fillRect(0, Math.random() * H, W, 2 + Math.random() * 14);
	}
}

// tv static: fresh noise every frame, scanlines, a rolling bar
function drawStatic(now: number) {
	const d = nimg.data;
	for (let i = 0; i < d.length; i += 4) {
		const v = Math.random() * 255;
		d[i] = d[i + 1] = d[i + 2] = v;
		d[i + 3] = 255;
	}
	nctx.putImageData(nimg, 0, 0);
	ctx.save();
	ctx.imageSmoothingEnabled = false;
	ctx.globalAlpha = 0.55;
	ctx.drawImage(noise, 0, 0, W, H);
	ctx.globalAlpha = 0.18;
	ctx.fillStyle = "#000";
	for (let y = 0; y < H; y += 3) ctx.fillRect(0, y, W, 1);
	ctx.globalAlpha = 0.12;
	ctx.fillStyle = "#fff";
	ctx.fillRect(0, ((now / 6) % (H + 80)) - 80, W, 60);
	ctx.restore();
}

// purge button cooldown bar: full right after firing, recedes right-to-left
const purgeBtn = document.getElementById("b-purge") as HTMLButtonElement;
// while the horn sweeps and analyses the bar charges up (left to right), holds full, then drains as the cooldown
let charge: { t0: number; dur: number } | null = null;
function updateCooldownBar() {
	let v: number;
	if (charge) v = Math.min(1, (Date.now() - charge.t0) / charge.dur);
	else v = Math.max(0, Math.min(1, (cooldownUntil - Date.now()) / COOLDOWN_MS));
	purgeBtn.style.setProperty("--cd", String(v));
}
let ping: { id: string; t0: number } | null = null;
const PING_MS = 2400;

// ---------------------------------------------------------------- modal
function openModal(html: string) {
	$("modalbody").innerHTML = html;
	$("modal").hidden = false;
}
const closeModal = () => {
	$("modal").hidden = true;
};
$("modalx").onclick = closeModal;
// close on backdrop click only if the press started on the backdrop too (a text-select drag that ends outside must not close it)
let downOnBackdrop = false;
$("modal").onmousedown = (e) => {
	downOnBackdrop = e.target === $("modal");
};
$("modal").onclick = (e) => {
	if (e.target === $("modal") && downOnBackdrop) closeModal();
	downOnBackdrop = false;
};

// ---------------------------------------------------------------- graph helpers
function bfs(
	start: string,
	g: Map<string, string[]> = adj,
): Map<string, number> {
	const d = new Map([[start, 0]]);
	const q = [start];
	while (q.length) {
		const u = need(q.shift());
		for (const v of g.get(u) ?? []) {
			if (!d.has(v) && !SPECIAL.has(v)) {
				d.set(v, need(d.get(u)) + 1);
				q.push(v);
			}
		}
	}
	return d;
}

// ---------------------------------------------------------------- map
const cv = $<HTMLCanvasElement>("map");
const ctx = need(cv.getContext("2d"));
let S = 1,
	W = 0,
	H = 0,
	K = 1,
	TX = 0,
	TY = 0; // base scale, canvas size, zoom, pan
let drag: {
	x0: number;
	y0: number;
	x1: number;
	y1: number;
	remove: boolean;
} | null = null;
let pan: { x: number; y: number } | null = null;
let hover: string | null = null;
let overCore = false;
const REALMS: Record<string, string> = {
	ASGR: "ASGARD",
	MIDG: "MIDGARD",
	VANA: "VANAHEIM",
	ALFH: "ALFHEIM",
	JOTN: "JOTUNHEIM",
	NIDV: "NIDAVELLIR",
	NIFL: "NIFLHEIM",
	HELH: "HELHEIM",
};
let hoverLabel: string | null = null;
const regionLabels: { name: string; x: number; y: number }[] = [];

function resize() {
	const r = cv.getBoundingClientRect(),
		dpr = window.devicePixelRatio || 1;
	cv.width = r.width * dpr;
	cv.height = r.height * dpr;
	ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
	W = r.width;
	H = r.height;
	S = Math.min(W, H) / 1000;
}
const sx = (x: number) => W / 2 + (x - 500) * S * K + TX;
const sy = (y: number) => H / 2 + (y - 500) * S * K + TY;
const RS = () => S * Math.sqrt(K); // node radius scale: grows slower than the map

function zoomAt(px: number, py: number, f: number) {
	const k2 = Math.min(8, Math.max(1, K * f)),
		r = k2 / K;
	TX = px - W / 2 - (px - W / 2 - TX) * r;
	TY = py - H / 2 - (py - H / 2 - TY) * r;
	K = k2;
	if (K === 1) {
		TX = 0;
		TY = 0;
	}
}

// HATI relay reach: time-based so a new run simply replaces the old one
const TICK = 170,
	DECAY = 2800;
let relay: { t0: number; hop: Map<string, number>; end: number } | null = null;
function relayLevel(id: string, now: number): number {
	if (!relay) return 0;
	const h = relay.hop.get(id);
	if (h === undefined) return 0;
	const age = now - relay.t0 - h * TICK;
	if (age < 0) return 0;
	return Math.max(0, 1 - age / DECAY) ** 1.5; // full brightness at once, then a taper
}

function nodeColor(n: GNode): string {
	const st = nstate.get(n.id) ?? "normal";
	if (st === "dark") return "#05070c";
	if (st === "amber") return "#ffb347";
	if (st === "red") return "#ff4a4a";
	if (st === "green") return "#6dff9c";
	if (n.status) return "#56606b";
	return "#4fd8ff";
}

function draw() {
	const now = performance.now();
	if (relay && now > relay.end) relay = null;
	ctx.clearRect(0, 0, W, H);
	ctx.lineWidth = 1;
	const rs = RS();
	for (const [a, b] of graph.links) {
		const A = need(byId.get(a)),
			B = need(byId.get(b));
		const sev = A.status || B.status;
		const dim = nstate.get(a) === "dark" || nstate.get(b) === "dark";
		ctx.strokeStyle = sev ? "#3a4450" : dim ? "#0a121d" : "#0d2438";
		ctx.setLineDash(sev ? [3, 4] : []);
		ctx.beginPath();
		ctx.moveTo(sx(A.x), sy(A.y));
		ctx.lineTo(sx(B.x), sy(B.y));
		ctx.stroke();
	}
	ctx.setLineDash([]);
	for (const n of graph.nodes) {
		const lv = relayLevel(n.id, now);
		if (lv > 0.01) {
			ctx.fillStyle = `rgba(255,190,100,${0.35 * lv})`;
			ctx.beginPath();
			ctx.arc(sx(n.x), sy(n.y), (3 + 4 * lv) * rs + 1, 0, 7);
			ctx.fill();
		}
	}
	for (const n of graph.nodes) {
		const lv = relayLevel(n.id, now);
		ctx.fillStyle =
			lv > 0.01
				? `rgb(${79 + 176 * lv},${216 - 20 * lv + 40 * lv},${255 - 100 * lv + 60 * lv})`
				: nodeColor(n);
		ctx.beginPath();
		ctx.arc(sx(n.x), sy(n.y), (2.6 + 1.6 * lv) * rs + 1, 0, 7);
		ctx.fill();
		if (n.id === "HATI") {
			ctx.strokeStyle = "#ffb347";
			ctx.beginPath();
			ctx.arc(sx(n.x), sy(n.y), 7 * rs + 2, 0, 7);
			ctx.stroke();
		}
		if (selected.has(n.id)) {
			ctx.strokeStyle = "#fff";
			ctx.lineWidth = 2;
			ctx.beginPath();
			ctx.arc(sx(n.x), sy(n.y), 6 * rs + 2, 0, 7);
			ctx.stroke();
			ctx.lineWidth = 1;
		}
	}
	if (ping) {
		const age = now - ping.t0;
		if (age > PING_MS) ping = null;
		else {
			const n = need(byId.get(ping.id));
			for (let k = 0; k < 3; k++) {
				const p = ((age - k * 350) / 1200) % 1;
				if (age - k * 350 < 0) continue;
				ctx.strokeStyle = `rgba(109,255,156,${1 - p})`;
				ctx.lineWidth = 2;
				ctx.beginPath();
				ctx.arc(sx(n.x), sy(n.y), (6 + 26 * p) * rs + 2, 0, 7);
				ctx.stroke();
			}
			ctx.lineWidth = 1;
		}
	}
	ctx.font = `${Math.max(10, 11 * S)}px ui-monospace, Menlo, monospace`;
	ctx.textAlign = "center";
	for (const l of regionLabels) {
		if (l.name === hoverLabel) continue; // hovered label is drawn last, on top (below)
		ctx.fillStyle = "#5b7088";
		ctx.fillText(l.name, sx(l.x), sy(l.y));
	}
	ctx.strokeStyle = "#ffb347";
	ctx.lineWidth = 2;
	for (const [a, b] of graph.core.strokes) {
		ctx.beginPath();
		ctx.moveTo(sx(a[0]), sy(a[1]));
		ctx.lineTo(sx(b[0]), sy(b[1]));
		ctx.stroke();
	}
	ctx.lineWidth = 1;
	ctx.fillStyle = "#5b7088";
	ctx.fillText("HEIMDALL CORE", sx(graph.core.x), sy(graph.core.y + 72));
	if (drag) {
		ctx.strokeStyle = drag.remove ? "#ff4a4a" : "#fff";
		ctx.setLineDash([4, 3]);
		ctx.strokeRect(drag.x0, drag.y0, drag.x1 - drag.x0, drag.y1 - drag.y0);
		ctx.setLineDash([]);
	}
	const tag = (
		t: string,
		x: number,
		y: number,
		align: "left" | "center",
		fg: string,
	) => {
		const fh = Math.max(10, 11 * S),
			w = ctx.measureText(t).width,
			px = 5,
			bh = fh + 8;
		const bx = align === "center" ? x - w / 2 - px : x - px;
		ctx.fillStyle = "#050b14";
		ctx.fillRect(bx, y - bh / 2, w + 2 * px, bh);
		ctx.strokeStyle = "#2a4a6a";
		ctx.lineWidth = 1;
		ctx.strokeRect(bx, y - bh / 2, w + 2 * px, bh);
		ctx.fillStyle = fg;
		ctx.textAlign = align;
		ctx.textBaseline = "middle";
		ctx.fillText(t, x, y);
		ctx.textBaseline = "alphabetic";
	};
	if (hover) {
		const n = need(byId.get(hover));
		tag(n.name, sx(n.x) + 14, sy(n.y) - 14, "left", "#fff");
	}
	const hl = regionLabels.find((l) => l.name === hoverLabel);
	if (hl)
		tag(
			REALMS[hl.name] ?? hl.name,
			sx(hl.x),
			sy(hl.y) - 4,
			"center",
			"#cfe3ff",
		);
	if (fx === "glitch") drawGlitch();
	else if (fx === "static") drawStatic(now);
	updateCooldownBar();
	if (banner) {
		ctx.textAlign = "center";
		const wrong = banner.startsWith("PURGE INC");
		ctx.font = `700 ${wrong ? Math.max(28, 52 * S) : Math.max(16, 22 * S)}px ui-monospace, Menlo, monospace`;
		ctx.fillStyle = banner.startsWith("THREAT")
			? "#6dff9c"
			: wrong
				? "#ff4a4a"
				: "#ffb347";
		if (wrong) {
			ctx.save();
			ctx.textBaseline = "middle";
			ctx.shadowColor = "#000";
			ctx.shadowBlur = 12;
			ctx.fillText(banner, W / 2, H / 2);
			ctx.restore();
		} else ctx.fillText(banner, W / 2, H - 24);
	}
	requestAnimationFrame(draw);
}

function pick(px: number, py: number): string | null {
	let best: string | null = null,
		bd = 12;
	for (const n of graph.nodes) {
		const d = Math.hypot(sx(n.x) - px, sy(n.y) - py);
		if (d < bd) {
			bd = d;
			best = n.id;
		}
	}
	return best;
}
const coreHit = (x: number, y: number) =>
	Math.hypot(x - sx(graph.core.x), y - sy(graph.core.y)) < 55 * S * K + 8;
const labelAt = (x: number, y: number) =>
	regionLabels.find(
		(l) => Math.abs(x - sx(l.x)) < 30 && Math.abs(y - sy(l.y)) < 10,
	);
const mouse = (e: MouseEvent) => {
	const r = cv.getBoundingClientRect();
	return [e.clientX - r.left, e.clientY - r.top] as const;
};

const HINT = $("nodeinfo").innerHTML;
function updateSel() {
	$("selinfo").textContent = `${selected.size} NODES SELECTED`;
	showInfo(hover ?? focus);
}
function showInfo(id: string | null) {
	if (!id) {
		$("nodeinfo").innerHTML = HINT;
		return;
	}
	const n = need(byId.get(id));
	const nb = (adj.get(id) ?? []).join(", ");
	$("nodeinfo").innerHTML =
		`<b style="color:#4fd8ff">${esc(n.name)}</b> &middot; REGION ${esc(n.region)} &middot; ` +
		`${n.status ? esc(n.status) : selected.has(n.id) ? "SELECTED FOR PURGE" : "ONLINE"}` +
		`${n.note ? ` &middot; ${esc(n.note)}` : ""}<br>LINKS: ${esc(nb)}`;
}

let dragMoved = false;
cv.addEventListener("contextmenu", (e) => e.preventDefault());
cv.addEventListener("mousedown", (e) => {
	const [x, y] = mouse(e);
	if (e.button === 2 || e.button === 1) {
		pan = { x, y };
		e.preventDefault();
		return;
	}
	if (e.button !== 0 || busy) return;
	drag = { x0: x, y0: y, x1: x, y1: y, remove: e.shiftKey };
	dragMoved = false;
});
cv.addEventListener("mousemove", (e) => {
	const [x, y] = mouse(e);
	if (pan) {
		TX += x - pan.x;
		TY += y - pan.y;
		pan = { x, y };
		cv.style.cursor = "grabbing";
		return;
	}
	if (drag) {
		drag.x1 = x;
		drag.y1 = y;
		if (Math.hypot(x - drag.x0, y - drag.y0) > 5) dragMoved = true;
	}
	const h = pick(x, y);
	if (h !== hover) {
		hover = h;
		showInfo(hover ?? focus);
	}
	overCore = coreHit(x, y);
	hoverLabel = labelAt(x, y)?.name ?? null;
	cv.style.cursor =
		drag && dragMoved
			? "crosshair"
			: overCore || hover || labelAt(x, y)
				? "pointer"
				: "default";
});
window.addEventListener("mouseup", () => {
	pan = null;
	if (!drag) return;
	if (dragMoved) {
		const [a, b] = [Math.min(drag.x0, drag.x1), Math.max(drag.x0, drag.x1)],
			[c, d] = [Math.min(drag.y0, drag.y1), Math.max(drag.y0, drag.y1)];
		for (const n of graph.nodes) {
			if (
				SPECIAL.has(n.id) ||
				sx(n.x) < a ||
				sx(n.x) > b ||
				sy(n.y) < c ||
				sy(n.y) > d
			)
				continue;
			if (drag.remove) selected.delete(n.id);
			else selected.add(n.id);
		}
		updateSel();
	}
	drag = null;
});
cv.addEventListener(
	"wheel",
	(e) => {
		e.preventDefault();
		const [x, y] = mouse(e);
		zoomAt(x, y, Math.exp(-e.deltaY * 0.003));
	},
	{ passive: false },
);
cv.addEventListener("click", (e) => {
	if (busy || dragMoved) {
		dragMoved = false;
		return;
	}
	const [x, y] = mouse(e);
	if (coreHit(x, y)) return openLedger();
	const lab = labelAt(x, y);
	if (lab) {
		const ids = graph.nodes
			.filter((n) => n.region === lab.name && !SPECIAL.has(n.id))
			.map((n) => n.id);
		const all = ids.every((i) => selected.has(i));
		for (const i of ids) {
			if (all) selected.delete(i);
			else selected.add(i);
		}
		return updateSel();
	}
	const id = pick(x, y);
	if (!id) return;
	focus = id;
	if (selected.has(id)) selected.delete(id);
	else selected.add(id);
	updateSel();
});
$("b-clear").onclick = () => {
	if (!busy) {
		selected.clear();
		updateSel();
	}
};
$("b-zin").onclick = () => zoomAt(W / 2, H / 2, 1.5);
$("b-zout").onclick = () => zoomAt(W / 2, H / 2, 1 / 1.5);
$("b-zreset").onclick = () => {
	K = 1;
	TX = 0;
	TY = 0;
};

// ping a satellite by its exact id (case-insensitive; no partial matches)
const pingQ = $<HTMLInputElement>("ping-q");
function doPing() {
	const q = pingQ.value.trim().toUpperCase();
	if (!q) return;
	const n = graph.nodes.find((x) => x.id.toUpperCase() === q);
	if (!n) {
		$("nodeinfo").innerHTML =
			`<span style="color:#ff4a4a">NO RESPONSE. NO SATELLITE WITH ID ${esc(q)}.</span>`;
		return;
	}
	focus = n.id;
	K = 3;
	TX = -(n.x - 500) * S * K;
	TY = -(n.y - 500) * S * K;
	ping = { id: n.id, t0: performance.now() };
	showInfo(n.id);
}
$("b-ping").onclick = doPing;
pingQ.addEventListener("keydown", (e) => {
	if (e.key === "Enter") doPing();
});

// relay trace: one hop per tick from HATI along the mesh; always restarts cleanly from HATI
$("b-relay").onclick = () => {
	if (busy) return;
	const hop = bfs("HATI", radj);
	relay = {
		t0: performance.now(),
		hop,
		end: performance.now() + Math.max(...hop.values()) * TICK + DECAY + 100,
	};
};

// ---------------------------------------------------------------- chat
let idx = 0,
	playing = true,
	speed = 1,
	typing = false;
const chatEl = $("chat"),
	scrub = $<HTMLInputElement>("c-scrub");

function rowHtml(m: Msg, text: string, cut: boolean) {
	const cls = m.kind === "system" ? "SYS" : m.label;
	return (
		`<div class="msg ${esc(cls)}" data-id="${m.id}"><span class="t">${m.ts.slice(11, 19)}</span>` +
		`<span class="l">${esc(m.label)}:</span><span class="x">${esc(text)}</span>${cut ? '<span class="cutmark"> ▮▮▮</span>' : ""}</div>`
	);
}
const extras: string[] = []; // post-solve lines (Surtr's last words, the flag): re-shown whenever the log is at its end
function addExtra(html: string) {
	extras.push(html);
	chatEl.insertAdjacentHTML("beforeend", html);
	chatEl.scrollTop = chatEl.scrollHeight;
}
function renderTo(n: number) {
	chatEl.innerHTML =
		chat
			.slice(0, n)
			.map((m) => rowHtml(m, m.text, m.cutAt !== undefined))
			.join("") + (n >= chat.length ? extras.join("") : "");
	chatEl.scrollTop = chatEl.scrollHeight;
	scrub.value = String(n);
	idx = n;
	scrub.style.setProperty("--p", `${(n / Math.max(1, chat.length)) * 100}%`);
	$("chatstate").textContent =
		`${n}/${chat.length} ${playing && n < chat.length ? "REPLAY" : n >= chat.length ? "END OF SCROLLBACK" : "PAUSED"}`;
}
// simple, robust loop: render completed rows, animate only the newest one
async function chatLoop() {
	for (;;) {
		if (playing && idx < chat.length && !typing) {
			typing = true;
			const m = chat[idx],
				at = idx,
				cut = m.cutAt !== undefined;
			renderTo(at);
			const holder = document.createElement("div");
			chatEl.appendChild(holder);
			const n = m.kind === "system" ? 0 : m.text.length;
			for (let i = 1; i <= n && playing && idx === at; i++) {
				holder.innerHTML = rowHtml(m, m.text.slice(0, i), cut && i === n);
				chatEl.scrollTop = chatEl.scrollHeight;
				await sleep((m.label === "HATI" ? 14 : 24) / speed);
			}
			if (idx === at && playing) {
				await sleep(450 / speed);
				if (idx === at) renderTo(at + 1);
			}
			typing = false;
		}
		await sleep(80);
	}
}
chatEl.addEventListener("click", (e) => {
	const row = (e.target as HTMLElement).closest(".msg") as HTMLElement | null;
	const m = row && chat.find((c) => c.id === row.dataset.id);
	if (!m) return;
	const f = m.frame;
	openModal(
		`<h2>FRAME ${esc(m.id)}</h2><table>` +
			[
				["sender", f.sender],
				["ts", m.ts],
				["sig", f.sig],
				["expectedSig", f.expectedSig],
				["origin", f.origin],
				["hops", f.hops.join(" > ")],
				["trace", f.trace],
				["note", f.note],
				["raw", f.raw],
			]
				.map(
					([k, v]) =>
						`<tr><td>${k}</td><td>${v === null || v === undefined ? "-" : esc(v)}</td></tr>`,
				)
				.join("") +
			"</table>",
	);
});
$("c-play").onclick = () => {
	playing = !playing;
	$("c-play").textContent = playing ? "PAUSE" : "PLAY";
	renderTo(idx);
};
scrub.oninput = () => {
	playing = false;
	$("c-play").textContent = "PLAY";
	renderTo(Number(scrub.value));
};
$<HTMLSelectElement>("c-speed").onchange = (e) => {
	speed = Number((e.target as HTMLSelectElement).value);
};
$("c-end").onclick = () => {
	playing = false;
	$("c-play").textContent = "PLAY";
	renderTo(chat.length);
};

function say(label: string, text: string, ts = "") {
	addExtra(
		`<div class="msg ${label}"><span class="t">${ts}</span><span class="l">${label}:</span><span class="x">${esc(text)}</span></div>`,
	);
}

// ---------------------------------------------------------------- CORE ledger + codex
const RUNES: [string, string][] = [
	["ᚠ", "F"],
	["ᚢ", "U"],
	["ᚦ", "TH"],
	["ᚨ", "A"],
	["ᚱ", "R"],
	["ᚲ", "K"],
	["ᚷ", "G"],
	["ᚹ", "W"],
	["ᚺ", "H"],
	["ᚾ", "N"],
	["ᛁ", "I"],
	["ᛃ", "J"],
	["ᛇ", "EI"],
	["ᛈ", "P"],
	["ᛉ", "Z"],
	["ᛊ", "S"],
	["ᛏ", "T"],
	["ᛒ", "B"],
	["ᛖ", "E"],
	["ᛗ", "M"],
	["ᛚ", "L"],
	["ᛜ", "NG"],
	["ᛞ", "D"],
	["ᛟ", "O"],
];

function openLedger() {
	openModal(`<h2>HEIMDALL CORE // ARMING LEDGER</h2><div class="sealed">SEALED</div>
    <canvas id="bind" width="560" height="190" style="width:100%;max-width:560px;display:block;margin:12px 0"></canvas>
    <p>SEALED IN THE ELDER SCRIPT. THE REALMS HOLD THE SEAL.</p>
    <p>WHERE THE SIGNAL GOES, THE SEAL FOLLOWS.</p>
    <button id="open-codex">ARCHIVE: ELDER SCRIPT</button>`);
	const c = document.getElementById("bind") as HTMLCanvasElement,
		g = need(c.getContext("2d"));
	const pts = graph.core.strokes.flat();
	const xs = pts.map((p) => p[0]),
		ys = pts.map((p) => p[1]);
	const x0 = Math.min(...xs),
		x1 = Math.max(...xs),
		y0 = Math.min(...ys),
		y1 = Math.max(...ys);
	const k = Math.min(500 / (x1 - x0), 150 / (y1 - y0));
	g.strokeStyle = "#ffb347";
	g.lineWidth = 5;
	g.lineCap = "round";
	for (const [a, b] of graph.core.strokes) {
		g.beginPath();
		g.moveTo(280 + (a[0] - (x0 + x1) / 2) * k, 95 + (a[1] - (y0 + y1) / 2) * k);
		g.lineTo(280 + (b[0] - (x0 + x1) / 2) * k, 95 + (b[1] - (y0 + y1) / 2) * k);
		g.stroke();
	}
	need(document.getElementById("open-codex")).onclick = () =>
		openModal(`<h2>ARCHIVE: ELDER SCRIPT</h2><p>THE 24 STAVES AND THEIR LATIN VALUES.</p>
      <div class="codex">${RUNES.map(([r, v]) => `<div><span class="runes">${r}</span><small>${v}</small></div>`).join("")}</div>`);
}

// ---------------------------------------------------------------- purge
function limitMsg(j: Record<string, unknown>) {
	const w = Number(j.retryAfter);
	return w > 0
		? `TOO MANY REQUESTS. TRY AGAIN IN ${w}s.`
		: "TOO MANY REQUESTS. WAIT A MOMENT.";
}

async function api(path: string, body: unknown) {
	const r = await fetch(path, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(body),
	});
	return {
		status: r.status,
		json: (await r.json().catch(() => ({}))) as Record<string, unknown>,
	};
}

const KEY_CODE = "gjh.code",
	KEY_TOKEN = "gjh.token";
const saved = (k: string) => {
	try {
		return sessionStorage.getItem(k) ?? "";
	} catch {
		return "";
	}
};
const save = (k: string, v: string) => {
	try {
		sessionStorage.setItem(k, v);
	} catch {
		/* storage unavailable */
	}
};

$("b-purge").onclick = () => {
	if (solved || busy || firing) return;
	openModal(`<h2>GJALLARHORN PURGE</h2>
    <label>ACTIVATION CODE</label>
    <div class="modalrow"><input type="text" id="p-code" autocomplete="off" spellcheck="false"><button id="p-code-chk">CHECK</button></div><div id="p-code-r"></div>
    <label>LAUNCH TOKEN</label>
    <div class="modalrow"><textarea id="p-token" spellcheck="false"></textarea><button id="p-token-chk">CHECK</button></div><div id="p-token-r"></div>
    <label>TARGET SECTOR</label><div id="p-sel"></div>
    <p><button id="p-fire" class="danger">FIRE</button> <span id="p-msg"></span></p>`);
	const codeEl = document.getElementById("p-code") as HTMLInputElement;
	const tokenEl = document.getElementById("p-token") as HTMLTextAreaElement;
	codeEl.value = saved(KEY_CODE);
	tokenEl.value = saved(KEY_TOKEN);
	codeEl.addEventListener("input", () => save(KEY_CODE, codeEl.value));
	tokenEl.addEventListener("input", () => save(KEY_TOKEN, tokenEl.value));
	const code = () => codeEl.value;
	const token = () => tokenEl.value.trim();
	need(document.getElementById("p-sel")).textContent = selected.size
		? `${selected.size} NODES: ${[...selected].sort().join(", ")}`
		: "NONE SELECTED. CLOSE THIS PANEL AND SELECT NODES ON THE MAP.";
	const chk = (kind: "code" | "token") => async () => {
		const out = need(document.getElementById(`p-${kind}-r`));
		const { status, json } = await api("/api/check", {
			[kind]: kind === "code" ? code() : token(),
		});
		out.innerHTML =
			status === 429
				? `<span class="bad">${limitMsg(json)}</span>`
				: json.ok
					? '<span class="ok">ACCEPTED</span>'
					: '<span class="bad">REJECTED</span>';
	};
	need(document.getElementById("p-code-chk")).onclick = chk("code");
	need(document.getElementById("p-token-chk")).onclick = chk("token");
	need(document.getElementById("p-fire")).onclick = () => fire(code(), token());
};

let firing = false; // true from pressing FIRE until the whole sequence is over
async function fire(code: string, token: string) {
	if (firing || busy || solved) return;
	firing = true;
	const fireBtn = document.getElementById("p-fire") as HTMLButtonElement | null;
	if (fireBtn) fireBtn.disabled = true;
	try {
		await fireInner(code, token);
	} finally {
		firing = false;
		if (fireBtn) fireBtn.disabled = false;
	}
}
async function fireInner(code: string, token: string) {
	const msg = need(document.getElementById("p-msg"));
	const wait = cooldownUntil - Date.now();
	if (wait > 0) {
		msg.innerHTML = `<span class="bad">COOLING DOWN ${Math.ceil(wait / 1000)}s</span>`;
		return;
	}
	if (!selected.size) {
		msg.innerHTML = '<span class="bad">NO TARGET SECTOR</span>';
		return;
	}
	// both keys must be right before anything fires: no sweep for a wrong code or token
	msg.textContent = "VERIFYING KEYS...";
	const [rc, rt] = await Promise.all([
		api("/api/check", { code }),
		api("/api/check", { token }),
	]).catch(() => [null, null]);
	if (!rc || !rt) {
		msg.innerHTML = '<span class="bad">NO ANSWER FROM THE CORE</span>';
		return;
	}
	if (rc.status === 429 || rt.status === 429) {
		msg.innerHTML = `<span class="bad">${limitMsg(rc.status === 429 ? rc.json : rt.json)}</span>`;
		return;
	}
	if (!rc.json.ok || !rt.json.ok) {
		msg.innerHTML = `<span class="bad">${!rc.json.ok ? "ACTIVATION CODE REJECTED" : "LAUNCH TOKEN REJECTED"}. THE HORN STAYS SILENT.</span>`;
		return;
	}
	msg.textContent = "";
	const targets = [...selected];
	// request starts now; its answer is not looked at until the fixed-length animation is over
	const reply = api("/api/purge", { code, token, nodes: targets }).catch(
		() => ({ status: 0, json: {} as Record<string, unknown> }),
	);
	const t0 = Date.now();
	const hop = bfs("HATI");
	const ordered = targets
		.slice()
		.sort(
			(a, b) => (hop.get(a) ?? 99) - (hop.get(b) ?? 99) || (a < b ? -1 : 1),
		);
	closeModal();
	busy = true;
	charge = { t0: Date.now(), dur: 4600 }; // sweep 2.4s + analyzing 2.2s (+ the held-back reply)
	banner = "TARGETING";
	for (let i = 0; i < ordered.length; i++) {
		nstate.set(ordered[i], "amber");
		await sleep(2400 / ordered.length);
	}
	banner = "CHARGING";
	await sleep(2200);
	const r = await reply;
	const left = 400 - (Date.now() - t0 - 4600); // keep timing identical whatever the answer
	if (left > 0) await sleep(left);
	if (
		r.status === 403 ||
		r.status === 400 ||
		r.status === 429 ||
		r.status === 0
	) {
		for (const n of ordered) nstate.delete(n);
		charge = null;
		banner = "";
		busy = false;
		openModal(
			`<h2>GJALLARHORN</h2><p class="bad">${r.status === 429 ? limitMsg(r.json) : r.status === 0 ? "NO ANSWER FROM THE CORE." : "AUTHORIZATION REJECTED. THE HORN STAYS SILENT."}</p>`,
		);
		return;
	}
	fx = "glitch";
	banner = "BLACKOUT";
	for (let i = 0; i < ordered.length; i++) {
		nstate.set(ordered[i], "dark");
		await sleep(2400 / ordered.length);
	}
	await sleep(900);
	fx = null;
	await sleep(1500); // beat of silence: no effect, banner still says BLACKOUT
	if (r.json.status === "neutralized") {
		charge = null;
		// finish the scrollback first so Surtr's last transmissions show (and aren't re-rendered over the replies below)
		playing = false;
		$("c-play").textContent = "PLAY";
		renderTo(chat.length);
		banner = "THREAT NEUTRALIZED";
		for (const n of graph.nodes)
			if (!SPECIAL.has(n.id)) nstate.set(n.id, "green");
		for (const t of ["...", "ok. you got me. this round.", "-dr"]) {
			say("HATI", t);
			await sleep(1200);
		}
		addExtra(`<div id="final">FLAG: ${esc(r.json.flag)}</div>`);
		solved = true;
		purgeBtn.disabled = true;
		purgeBtn.textContent = "SPENT";
		busy = false;
		return;
	}
	banner = "PURGE INCOMPLETE. THREAT PERSISTS.";
	for (const n of graph.nodes) if (!SPECIAL.has(n.id)) nstate.set(n.id, "red"); // Surtr self-heals
	fx = "static";
	await sleep(2600);
	fx = null;
	nstate.clear();
	cooldownUntil = Date.now() + COOLDOWN_MS;
	charge = null;
	banner = "";
	busy = false;
}

// ---------------------------------------------------------------- boot
async function boot() {
	const [g, c] = await Promise.all([
		fetch("graph.json").then((r) => r.json()),
		fetch("chat.json").then((r) => r.json()),
	]);
	graph = g;
	chat = c.messages;
	for (const n of graph.nodes) {
		byId.set(n.id, n);
		adj.set(n.id, []);
	}
	for (const [a, b] of graph.links) {
		adj.get(a)?.push(b);
		adj.get(b)?.push(a);
	}
	for (const n of graph.nodes) radj.set(n.id, []);
	for (const [a, b] of graph.relay) {
		radj.get(a)?.push(b);
		radj.get(b)?.push(a);
	}
	for (const r of graph.regions) {
		const ns = graph.nodes.filter((n) => n.region === r);
		const cx = ns.reduce((s, n) => s + n.x, 0) / ns.length,
			cy = ns.reduce((s, n) => s + n.y, 0) / ns.length;
		const dx = cx - 500,
			dy = cy - 500,
			L = Math.hypot(dx, dy) || 1;
		// sit just beyond the outermost node of the cluster along the outward radial
		const reach =
			Math.max(...ns.map((n) => ((n.x - cx) * dx + (n.y - cy) * dy) / L)) + 30;
		regionLabels.push({
			name: r,
			x: cx + (dx / L) * reach,
			y: cy + (dy / L) * reach,
		});
	}
	scrub.max = String(chat.length);
	window.addEventListener("resize", resize);
	resize();
	requestAnimationFrame(draw);
	const today = new Date();
	$("clock").textContent =
		`2074-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")} // LIVE`;
	void chatLoop();
}
void boot();
