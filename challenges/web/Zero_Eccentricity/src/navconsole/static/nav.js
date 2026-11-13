// NAV-7 orbit insertion console.
// Records one pointer stroke, signs it for the current round, and sends it
// to the burn computer (/api/transmit) for scoring.
(function () {
  "use strict";

  var SIZE = 600, PX = 300, PY = 300, PR = 36;

  // ---- SHA-256 / HMAC (crypto.subtle is unavailable on plain-http hosts) ----
  var K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ];

  function bytes(str) {           // ASCII-only inputs here
    var out = new Array(str.length);
    for (var i = 0; i < str.length; i++) out[i] = str.charCodeAt(i) & 0xff;
    return out;
  }

  function sha256(msg) {          // msg: array of bytes -> array of 32 bytes
    var H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    var m = msg.slice(), bitLen = msg.length * 8;
    m.push(0x80);
    while (m.length % 64 !== 56) m.push(0);
    var hi = Math.floor(bitLen / 0x100000000), lo = bitLen >>> 0;
    m.push((hi >>> 24) & 255, (hi >>> 16) & 255, (hi >>> 8) & 255, hi & 255,
           (lo >>> 24) & 255, (lo >>> 16) & 255, (lo >>> 8) & 255, lo & 255);
    var w = new Array(64);
    for (var off = 0; off < m.length; off += 64) {
      for (var i = 0; i < 16; i++) {
        w[i] = (m[off + 4 * i] << 24) | (m[off + 4 * i + 1] << 16) | (m[off + 4 * i + 2] << 8) | m[off + 4 * i + 3];
      }
      for (i = 16; i < 64; i++) {
        var a15 = w[i - 15], a2 = w[i - 2];
        var s0 = ((a15 >>> 7) | (a15 << 25)) ^ ((a15 >>> 18) | (a15 << 14)) ^ (a15 >>> 3);
        var s1 = ((a2 >>> 17) | (a2 << 15)) ^ ((a2 >>> 19) | (a2 << 13)) ^ (a2 >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
      }
      var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
      for (i = 0; i < 64; i++) {
        var S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
        var ch = (e & f) ^ (~e & g);
        var t1 = (h + S1 + ch + K[i] + w[i]) | 0;
        var S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
        var maj = (a & b) ^ (a & c) ^ (b & c);
        var t2 = (S0 + maj) | 0;
        h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
      }
      H[0] = (H[0] + a) | 0; H[1] = (H[1] + b) | 0; H[2] = (H[2] + c) | 0; H[3] = (H[3] + d) | 0;
      H[4] = (H[4] + e) | 0; H[5] = (H[5] + f) | 0; H[6] = (H[6] + g) | 0; H[7] = (H[7] + h) | 0;
    }
    var out = [];
    for (i = 0; i < 8; i++) out.push((H[i] >>> 24) & 255, (H[i] >>> 16) & 255, (H[i] >>> 8) & 255, H[i] & 255);
    return out;
  }

  function hmacHex(keyStr, msgStr) {
    var key = bytes(keyStr);
    if (key.length > 64) key = sha256(key);
    while (key.length < 64) key.push(0);
    var ipad = key.map(function (x) { return x ^ 0x36; });
    var opad = key.map(function (x) { return x ^ 0x5c; });
    var inner = sha256(ipad.concat(bytes(msgStr)));
    var mac = sha256(opad.concat(inner));
    return mac.map(function (x) { return (x < 16 ? "0" : "") + x.toString(16); }).join("");
  }

  // Must match canonical() in app.py byte for byte.
  function canonical(points) {
    return points.map(function (p) { return p[0].toFixed(2) + "," + p[1].toFixed(2) + "," + p[2]; }).join(";");
  }

  // ---- scope scenery (vector phosphor) ----
  var PH = "125,255,154";
  var sky = document.getElementById("sky").getContext("2d");
  function drawScope() {
    var g = sky;
    g.fillStyle = "#030a05"; g.fillRect(0, 0, SIZE, SIZE);
    g.lineCap = "round";

    // faint phosphor grain
    var seed = 11;
    function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    for (var i = 0; i < 900; i++) {
      g.fillStyle = "rgba(" + PH + "," + (rnd() * 0.05).toFixed(3) + ")";
      g.fillRect(rnd() * SIZE, rnd() * SIZE, 1, 1);
    }

    // range rings, labelled in thousands of km
    g.font = "10px 'Lucida Console', 'Courier New', monospace";
    g.textAlign = "left";
    for (var r = 60, n = 1; r <= 280; r += 60, n++) {
      g.strokeStyle = "rgba(" + PH + ",0.10)"; g.lineWidth = 1;
      g.setLineDash(r % 120 === 0 ? [] : [2, 5]);
      g.beginPath(); g.arc(PX, PY, r, 0, Math.PI * 2); g.stroke();
      g.fillStyle = "rgba(" + PH + ",0.32)";
      g.fillText((n * 2.4).toFixed(1), PX + 4, PY - r - 3);
    }
    g.setLineDash([]);

    // crosshair
    g.strokeStyle = "rgba(" + PH + ",0.09)";
    g.beginPath(); g.moveTo(PX, 20); g.lineTo(PX, SIZE - 20); g.moveTo(20, PY); g.lineTo(SIZE - 20, PY); g.stroke();

    // bearing ticks around the edge
    for (var d = 0; d < 360; d += 5) {
      var a = d * Math.PI / 180, long = d % 30 === 0, r0 = long ? 276 : 283;
      g.strokeStyle = "rgba(" + PH + "," + (long ? 0.45 : 0.2) + ")";
      g.beginPath();
      g.moveTo(PX + r0 * Math.sin(a), PY - r0 * Math.cos(a));
      g.lineTo(PX + 290 * Math.sin(a), PY - 290 * Math.cos(a));
      g.stroke();
      if (long && d % 90 !== 0) {
        g.fillStyle = "rgba(" + PH + ",0.35)"; g.textAlign = "center";
        g.fillText(("00" + d).slice(-3), PX + 264 * Math.sin(a), PY - 264 * Math.cos(a) + 3);
      }
    }

    // wireframe planet
    g.save();
    g.shadowColor = "rgba(" + PH + ",0.8)"; g.shadowBlur = 6;
    g.strokeStyle = "rgba(" + PH + ",0.85)"; g.lineWidth = 1.3;
    g.beginPath(); g.arc(PX, PY, PR, 0, Math.PI * 2); g.stroke();
    g.lineWidth = 0.8; g.strokeStyle = "rgba(" + PH + ",0.45)";
    g.translate(PX, PY); g.rotate(-0.38);
    for (var k = -2; k <= 2; k++) {               // latitude lines
      var y = k * PR / 3, w = Math.sqrt(PR * PR - y * y);
      g.beginPath(); g.ellipse(0, y, w, w * 0.22, 0, 0, Math.PI * 2); g.stroke();
    }
    for (var m = 1; m <= 3; m++) {                // meridians
      g.beginPath(); g.ellipse(0, 0, PR * m / 4, PR, 0, 0, Math.PI * 2); g.stroke();
    }
    g.restore();

    g.fillStyle = "rgba(" + PH + ",0.55)"; g.textAlign = "left";
    g.fillText("KESSLER-IV", PX + PR + 8, PY + PR + 2);
  }

  // ---- seven-segment readouts ----
  //   segments: a b c d e f g  (top, upper-right, lower-right, bottom, lower-left, upper-left, middle)
  var SEG = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
    "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""
  };
  var segState = {};                    // id -> [text, digits], redrawn on resize
  var segScale = 1;
  function drawSeg(id, text, digits) {
    segState[id] = [text, digits];
    var c = document.getElementById(id), g = c.getContext("2d");
    if (!c.dataset.w) { c.dataset.w = c.width; c.dataset.h = c.height; }
    var W = +c.dataset.w, H = +c.dataset.h, pad = 4;
    c.style.width = W + "px"; c.style.height = H + "px";
    var bw = Math.round(W * segScale), bh = Math.round(H * segScale);
    if (c.width !== bw || c.height !== bh) { c.width = bw; c.height = bh; }
    g.setTransform(segScale, 0, 0, segScale, 0, 0);
    var cellW = (W - pad * 2) / digits, dw = cellW * 0.72, dh = H - pad * 2, t = Math.max(3, dh * 0.11);
    g.clearRect(0, 0, W, H);
    // right-align text into `digits` cells; '.' attaches to the previous cell
    var cells = [], i;
    for (i = 0; i < text.length; i++) {
      if (text[i] === "." && cells.length) cells[cells.length - 1].dot = true;
      else cells.push({ ch: text[i], dot: false });
    }
    while (cells.length < digits) cells.unshift({ ch: " ", dot: false });
    cells = cells.slice(-digits);

    function seg(x, y, name, on) {
      g.fillStyle = on ? "#ff3b1f" : "rgba(255,59,31,0.09)";
      g.shadowColor = on ? "rgba(255,70,30,0.8)" : "transparent";
      g.shadowBlur = on ? 6 : 0;
      var s = 0.12 * dw, h2 = dh / 2;                    // slant
      function quad(x1, y1, x2, y2, horiz) {
        g.beginPath();
        if (horiz) {
          g.moveTo(x1 + t / 2, y1); g.lineTo(x1 + t, y1 - t / 2); g.lineTo(x2 - t, y2 - t / 2);
          g.lineTo(x2 - t / 2, y2); g.lineTo(x2 - t, y2 + t / 2); g.lineTo(x1 + t, y1 + t / 2);
        } else {
          g.moveTo(x1, y1 + t / 2); g.lineTo(x1 + t / 2, y1 + t); g.lineTo(x2 + t / 2, y2 - t);
          g.lineTo(x2, y2 - t / 2); g.lineTo(x2 - t / 2, y2 - t); g.lineTo(x1 - t / 2, y1 + t);
        }
        g.closePath(); g.fill();
      }
      var X = function (yy) { return x + s * (1 - (yy - y) / dh); };   // italic lean
      var y0 = y, y1 = y + h2, y2 = y + dh;
      if (name === "a") quad(X(y0), y0, X(y0) + dw - t, y0, true);
      if (name === "g") quad(X(y1), y1, X(y1) + dw - t, y1, true);
      if (name === "d") quad(X(y2), y2, X(y2) + dw - t, y2, true);
      if (name === "f") quad(X(y0), y0, X(y1), y1, false);
      if (name === "e") quad(X(y1), y1, X(y2), y2, false);
      if (name === "b") quad(X(y0) + dw - t, y0, X(y1) + dw - t, y1, false);
      if (name === "c") quad(X(y1) + dw - t, y1, X(y2) + dw - t, y2, false);
    }
    for (i = 0; i < cells.length; i++) {
      var x = pad + i * cellW + t / 2, lit = SEG[cells[i].ch] || "";
      "abcdefg".split("").forEach(function (n) { seg(x, pad, n, lit.indexOf(n) >= 0); });
      g.fillStyle = cells[i].dot ? "#ff3b1f" : "rgba(255,59,31,0.09)";
      g.shadowBlur = cells[i].dot ? 6 : 0;
      g.beginPath(); g.arc(x + dw - t / 2 + cellW * 0.14, pad + dh, t * 0.55, 0, Math.PI * 2); g.fill();
    }
  }
  function blankReadouts() {
    drawSeg("seg-circ", "--.--", 5);
    drawSeg("seg-ecc", "-.----", 5);
    drawSeg("seg-rad", "---.-", 5);
  }
  // ---- UI ----
  var cv = document.getElementById("trace"), ctx = cv.getContext("2d");

  // ---- fit the console to the window ----
  // The whole panel is CSS-scaled to fill the viewport. Canvas backing stores
  // are resized to match so nothing goes blurry; drawing still happens in the
  // fixed 600x600 scope coordinate system (local() maps the pointer into it).
  var panel = document.querySelector(".panel");
  function fit() {
    var s = Math.min((window.innerWidth - 40) / panel.offsetWidth,
                     (window.innerHeight - 40) / panel.offsetHeight);
    s = Math.max(0.4, Math.min(s, 2.2));
    panel.style.transform = "scale(" + s + ")";
    var dpr = window.devicePixelRatio || 1, k = s * dpr, px = Math.round(SIZE * k);
    [document.getElementById("sky"), cv].forEach(function (c) {
      if (c.width !== px) { c.width = px; c.height = px; }
      c.getContext("2d").setTransform(px / SIZE, 0, 0, px / SIZE, 0, 0);
    });
    drawScope();
    if (drawing) abort("Trace interrupted.");
    segScale = k;
    Object.keys(segState).forEach(function (id) { drawSeg(id, segState[id][0], segState[id][1]); });
  }
  blankReadouts();
  fit();
  window.addEventListener("resize", fit);
  var $ = function (id) { return document.getElementById(id); };
  var LAMPS = { xmit: "lamp-xmit", unstable: "lamp-unstable", reject: "lamp-reject", lock: "lamp-lock" };
  function lamps(on) {
    Object.keys(LAMPS).forEach(function (k) { $(LAMPS[k]).classList.toggle("on", on.indexOf(k) >= 0); });
  }
  function setStatus(text, cls) {
    $("status").textContent = text;
    $("status").className = cls || "";
    if (cls === "bad") lamps(["reject"]);
  }

  var round = null, busy = false;
  function newRound() {
    round = null;
    return fetch("/api/round", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (j) { round = j; })
      .catch(function () { setStatus("Burn computer unreachable.", "bad"); });
  }

  // ---- stroke capture ----
  var drawing = false, pts = [], t0 = 0, rect = null;

  function local(e) {
    var x = (e.clientX - rect.left) * (SIZE / rect.width);
    var y = (e.clientY - rect.top) * (SIZE / rect.height);
    return [Math.round(x * 100) / 100, Math.round(y * 100) / 100];
  }

  function abort(msg) {
    drawing = false; pts = [];
    ctx.clearRect(0, 0, SIZE, SIZE);
    setStatus(msg, "bad");
  }

  cv.addEventListener("pointerdown", function (e) {
    if (!e.isTrusted) { abort("Synthetic input detected. Manual control only."); return; }
    if (busy || !round || e.button !== 0) return;
    rect = cv.getBoundingClientRect();
    try { cv.setPointerCapture(e.pointerId); } catch (_) {}
    drawing = true; t0 = e.timeStamp; pts = [];
    var p = local(e); pts.push([p[0], p[1], 0]);
    ctx.clearRect(0, 0, SIZE, SIZE);
    ctx.strokeStyle = "rgba(" + PH + ",0.95)"; ctx.lineWidth = 2; ctx.lineCap = "round"; ctx.lineJoin = "round";
    ctx.shadowColor = "rgba(" + PH + ",0.9)"; ctx.shadowBlur = 7;
    ctx.beginPath(); ctx.moveTo(p[0], p[1]);
    lamps([]); blankReadouts();
    $("tape").classList.remove("out");
    setStatus("Recording trace", "warn");
  });

  cv.addEventListener("pointermove", function (e) {
    if (!drawing) return;
    if (!e.isTrusted) { abort("Synthetic input detected. Manual control only."); return; }
    var p = local(e), t = Math.round(e.timeStamp - t0);
    var last = pts[pts.length - 1];
    if (t < last[2]) t = last[2];
    pts.push([p[0], p[1], t]);
    ctx.lineTo(p[0], p[1]); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(p[0], p[1]);
  });

  function finish(e) {
    if (!drawing) return;
    if (!e.isTrusted) { abort("Synthetic input detected. Manual control only."); return; }
    drawing = false;
    var stroke = pts; pts = [];
    if (stroke.length < 60) { setStatus("Trace too short. Draw a full orbit.", "bad"); return; }
    transmit(stroke);
  }
  cv.addEventListener("pointerup", finish);
  cv.addEventListener("pointercancel", function () { abort("Trace interrupted."); });

  function transmit(stroke) {
    busy = true;
    lamps(["xmit"]);
    setStatus("Transmitting to burn computer", "warn");
    var body = {
      round_id: round.round_id,
      points: stroke,
      sig: hmacHex(round.nonce, canonical(stroke))
    };
    fetch("/api/transmit", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (typeof j.circularity === "number") {
          drawSeg("seg-circ", j.circularity.toFixed(2), 5);
          drawSeg("seg-ecc", Math.min(j.eccentricity, 9.9999).toFixed(4), 5);
          drawSeg("seg-rad", Math.min(j.radius, 999.9).toFixed(1), 5);
        }
        var locked = j.status === "locked";
        setStatus(j.message || "No response.", locked ? "good" : "bad");
        if (j.status === "unstable") lamps(["unstable"]);
        if (locked) {
          lamps(["lock"]);
          $("flag").textContent = "BURN COMMITTED  T+00:00:00\n" + j.flag;
          $("tape").classList.add("out");
        } else {
          $("flag").textContent = "";
        }
      })
      .catch(function () { setStatus("Burn computer unreachable.", "bad"); })
      .then(function () { busy = false; return newRound(); });
  }

  newRound();
})();
