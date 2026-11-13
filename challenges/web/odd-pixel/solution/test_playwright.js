const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
// Browser smoke test: rejection paths, then a scripted solve. Never print the flag.
// Usage: node solution/test_playwright.js [http://host:port/] [screenshot dir]
const URL = process.argv[2] || 'http://localhost:8000/', OUT = process.argv[3];
if (OUT) fs.mkdirSync(OUT, { recursive: true });
const loaded = p => p.waitForFunction(() => { const i = document.getElementById('img'); return i.complete && i.naturalWidth > 0; });
const result = async p => { await p.waitForFunction(() => document.getElementById('res').textContent); return p.textContent('#res'); };
const screenshot = (p, name) => OUT && p.screenshot({ path: `${OUT}/${name}` });
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
  const p = await b.newPage({ viewport: { width: 900, height: 900 } });
  // 1. human guess: click the middle
  await p.goto(URL); await loaded(p); await p.waitForTimeout(1200);
  await screenshot(p, '1-console.png');
  const wrong = await p.evaluate(() => {
    const img = document.getElementById('img'), canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d'); ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data, counts = {};
    for (let i = 0; i < data.length; i += 4) counts[data[i]] = (counts[data[i]] || 0) + 1;
    const common = +Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0];
    for (let i = 0; i < data.length; i += 4) if (data[i] !== common) {
      const x = (i / 4) % canvas.width, y = Math.floor(i / 4 / canvas.width);
      return [(x + 1) % canvas.width, y];
    }
  });
  await p.click('#img', { position: { x: wrong[0] + 0.5, y: wrong[1] + 0.5 } });
  assert.match(await result(p), /READ REJECTED/);
  // 2. too slow: wait 6 s then click
  await p.goto(URL); await loaded(p); await p.waitForTimeout(6000);
  await screenshot(p, '2-window-closed.png');
  await p.click('#img', { position: { x: 10, y: 10 } });
  assert.match(await result(p), /READ REJECTED/);
  // 3. player script in the browser console: read pixels via canvas, click the odd one
  await p.goto(URL); await loaded(p);
  const t0 = Date.now();
  const [x, y] = await p.evaluate(() => {
    const img = document.getElementById('img'), c = document.createElement('canvas');
    c.width = img.naturalWidth; c.height = img.naturalHeight;
    const ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0);
    const d = ctx.getImageData(0, 0, c.width, c.height).data, cnt = {};
    for (let i = 0; i < d.length; i += 4) cnt[d[i]] = (cnt[d[i]] || 0) + 1;
    const common = +Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a])[0];
    for (let i = 0; i < d.length; i += 4) if (d[i] != common) return [(i / 4) % c.width, Math.floor(i / 4 / c.width)];
  });
  const r = await p.evaluate(() => { const i = document.getElementById('img'), b = i.getBoundingClientRect(); return [b.left + i.clientLeft, b.top + i.clientTop]; });
  await p.mouse.click(r[0] + x + 0.5, r[1] + y + 0.5);
  assert.match(await result(p), /ANOMALY CONFIRMED/);
  await b.close();
  console.log(`PASS: browser solve completed in ${Date.now() - t0} ms`);
})();
