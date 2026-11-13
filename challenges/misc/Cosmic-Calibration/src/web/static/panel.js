// RASA calibration panel. Draws what the server reports and sends it key
// presses; the panel's state and its checks all live on the server.
"use strict";

const canvas = document.getElementById("sky");
const ctx = canvas.getContext("2d");
const W = canvas.width, H = canvas.height;
const PX = 2;  // canvas pixels per pixel of the 960x480 design

const INK = "rgb(232,236,250)";
const RING_STYLE = [[INK, 2], ["rgb(112,122,165)", 2], [INK, 4]];  // near/mid/far
const STAR_ALPHA = 0.55;
const KEYS = "udlrfbmes";  // plus x y z, which the server spells in lower case

const overlays = {};
for (const id of ["start", "help", "solved"]) overlays[id] = document.getElementById(id);
const hint = document.getElementById("hint");
const shown = (id) => !overlays[id].hidden;
const show = (id, on) => { overlays[id].hidden = !on; };

let layout = null, dots = [], anim = null;
let zoom = 1, offset = [0, 0], dotSize = 3;
let wasSolved = false, flag = null;
const queue = [];
let busy = false;

// ---------------------------------------------------------------- the view
function fit() {
  const r = layout.radii[2];
  const xs = layout.centres.map((c) => c[0]), ys = layout.centres.map((c) => c[1]);
  const lo = [Math.min(...xs) - r, Math.min(...ys) - r];
  const hi = [Math.max(...xs) + r, Math.max(...ys) + r];
  zoom = Math.min(W * 0.96 / (hi[0] - lo[0]), H * 0.94 / (hi[1] - lo[1]));
  offset = [W / 2 - (lo[0] + hi[0]) / 2 * zoom, H / 2 - (lo[1] + hi[1]) / 2 * zoom];
  sizeDots();
}

function sizeDots() {
  dotSize = Math.max(3 * PX, Math.round(0.31 * layout.gap * zoom));
  sprites.clear();
}

function setZoom(factor) {
  const next = Math.min(Math.max(zoom * factor, H * 0.03), H * 20);
  const f = next / zoom;
  zoom = next;
  offset = [(offset[0] - W / 2) * f + W / 2, (offset[1] - H / 2) * f + H / 2];
  sizeDots();
}

const project = (q) => [q[0] * zoom + offset[0], q[1] * zoom + offset[1]];

// ---------------------------------------------------------------- the dots
const sprites = new Map();

function sprite(col) {
  const key = col.join();
  if (sprites.has(key)) return sprites.get(key);
  const r = dotSize, half = Math.ceil(r * 2.3) + 1, size = 2 * half + 1;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const g = c.getContext("2d"), img = g.createImageData(size, size);
  const clip = (v) => Math.min(Math.max(v, 0), 1);
  const reach = 2.2 * r, w = 0.75 * PX;
  for (let j = 0; j < size; j++) {
    for (let i = 0; i < size; i++) {
      const x = i - half, y = j - half, d = Math.hypot(x, y);
      const glow = d > r ? 0.32 * clip(1 - (d - r) / (1.1 * r)) ** 2 : 0;
      const body = STAR_ALPHA * clip(r + 0.5 - d);
      const colour = 1 - (1 - glow) * (1 - body);
      const core = 0.85 * Math.exp(-((d / (0.36 * r)) ** 2));
      const spikes = d > 0.8 * r
        ? 0.5 * (Math.exp(-((x / w) ** 2)) * clip(1 - Math.abs(y) / reach)
               + Math.exp(-((y / w) ** 2)) * clip(1 - Math.abs(x) / reach)) : 0;
      const rim = 0.9 * clip(1 - Math.abs(d - r) / (0.9 * PX));
      const white = 1 - (1 - core) * (1 - Math.min(spikes, 1)) * (1 - rim);
      const a = white + colour * (1 - white), k = 4 * (j * size + i);
      for (let n = 0; n < 3; n++) {
        img.data[k + n] = (255 * white + col[n] * colour * (1 - white)) / Math.max(a, 1e-6);
      }
      img.data[k + 3] = 255 * a;
    }
  }
  g.putImageData(img, 0, 0);
  const made = { canvas: c, half };
  sprites.set(key, made);
  return made;
}

function drawDot(col, q) {
  const [x, y] = project(q), s = sprite(col);
  ctx.drawImage(s.canvas, Math.round(x) - s.half, Math.round(y) - s.half);
}

// A dot's place a fraction s of the way along its path around the pivot.
function along(dot, s) {
  if (!dot.pivot) return dot.from;
  const [px, py] = dot.pivot;
  const v0 = [dot.from[0] - px, dot.from[1] - py], v1 = [dot.to[0] - px, dot.to[1] - py];
  const r0 = Math.hypot(...v0), r1 = Math.hypot(...v1);
  if (r0 < 1e-9) return dot.from;
  const f0 = Math.atan2(v0[1], v0[0]), f1 = Math.atan2(v1[1], v1[0]);
  const tau = 2 * Math.PI, turn = dot.sense * (f1 - f0);
  const delta = dot.sense * (((turn % tau) + tau) % tau);
  const f = f0 + delta * s, r = r0 + (r1 - r0) * s;
  return [px + r * Math.cos(f), py + r * Math.sin(f)];
}

// ---------------------------------------------------------------- the sky
const TINTS = [[255, 255, 255], [198, 214, 255], [255, 234, 200]];
const stars = Array.from({ length: 480 }, () => ({
  x: Math.random() * W, y: Math.random() * H,
  size: [1, 1, 1, 1, 2, 2, 3][Math.floor(Math.random() * 7)],
  level: 0.3 + Math.random() * 0.55,
  speed: 0.4 + Math.random() * 1.4,
  phase: Math.random() * 2 * Math.PI,
  tint: TINTS[Math.random() < 0.6 ? 0 : Math.random() < 0.6 ? 1 : 2],
}));
const gradient = ctx.createLinearGradient(0, 0, 0, H);
gradient.addColorStop(0, "rgb(1,1,5)");
gradient.addColorStop(1, "rgb(7,8,20)");

function drawSky(t) {
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, W, H);
  for (const s of stars) {
    const level = (s.level + 0.05 * s.size) * (0.7 + 0.3 * Math.sin(s.speed * t + s.phase));
    const x = (s.x + t * 0.6 * PX * s.size) % W, side = s.size * PX;
    ctx.fillStyle = `rgba(${s.tint},${Math.min(1, level)})`;
    ctx.fillRect(x, s.y, side, side);
  }
}

function drawRings() {
  for (const c of layout.centres) {
    const [x, y] = project(c);
    layout.radii.forEach((r, i) => {
      ctx.strokeStyle = RING_STYLE[i][0];
      ctx.lineWidth = RING_STYLE[i][1] * PX;
      ctx.beginPath();
      ctx.arc(x, y, r * zoom, 0, 2 * Math.PI);
      ctx.stroke();
    });
  }
}

function frame(now) {
  drawSky(now / 1000);
  if (layout) {
    drawRings();
    if (anim) {
      const k = Math.min((now - (anim.start ??= now)) / anim.ms, 1);
      const s = k * k * (3 - 2 * k);
      const moving = anim.dots.filter((d) => d.pivot);
      for (const d of anim.dots) if (!d.pivot) drawDot(d.col, d.from);
      for (const d of moving) drawDot(d.col, along(d, s));  // moving dots on top
      if (k >= 1) { const done = anim.done; anim = null; done(); }
    } else {
      for (const d of dots) drawDot(d.col, d.xy);
    }
  }
  requestAnimationFrame(frame);
}

// ---------------------------------------------------------------- the server
async function call(path, options) {
  const res = await fetch(path, { credentials: "same-origin", ...options });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

function apply(state) {
  dots = state.dots;
  flag = state.solved ? state.flag : null;
  announce();
}

function announce() {
  if (shown("start")) return;
  if (flag && !wasSolved) {  // just solved: show the flag
    document.getElementById("flag").textContent = flag;
    show("help", false);
    show("solved", true);
  }
  wasSolved = Boolean(flag);
}

async function drain() {
  if (busy) return;
  busy = true;
  try {
    while (queue.length) {
      const state = await call("/api/moves", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ moves: queue.shift() }),
      });
      const ms = queue.length > 3 ? 83 : 233;
      await new Promise((done) => { anim = { dots: state.turn, ms, done }; });
      apply(state);
    }
  } catch (e) {
    queue.length = 0;
    hint.textContent = "Lost contact with the panel. Reload the page.";
  }
  busy = false;
}

// ---------------------------------------------------------------- input
function closeStart() {
  show("start", false);
  announce();
}

addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (shown("start")) {
    e.preventDefault();
    return closeStart();
  }
  if (e.key === "Escape") {
    if (shown("solved")) show("solved", false);
    else show("help", !shown("help"));
    return;
  }
  if (shown("help") || shown("solved")) return;
  const key = e.key.toLowerCase();
  const name = KEYS.includes(key) ? key.toUpperCase() : "xyz".includes(key) ? key : null;
  if (key.length !== 1 || !name) return;
  e.preventDefault();
  queue.push(e.shiftKey ? name + "'" : name);
  drain();
});

for (const id of ["help", "solved"]) {
  overlays[id].addEventListener("click", (e) => {
    if (e.target === overlays[id]) show(id, false);  // clicks on the panel can select the flag
  });
}
overlays.start.addEventListener("click", closeStart);

canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  if (layout && !shown("start")) setZoom(1.1 ** (e.deltaY < 0 ? 1 : -1));
}, { passive: false });

document.getElementById("restart").addEventListener("click", async (e) => {
  e.currentTarget.blur();
  if (!confirm("Restart the calibration from the beginning?")) return;
  queue.length = 0;
  wasSolved = false;
  apply(await call("/api/new", { method: "POST" }));
});

// ---------------------------------------------------------------- go
call("/api/state").then((state) => {
  layout = state.layout;
  fit();
  apply(state);
}).catch(() => { hint.textContent = "Could not reach the panel. Reload the page."; });
requestAnimationFrame(frame);
