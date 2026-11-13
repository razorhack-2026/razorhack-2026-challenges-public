# Zero Eccentricity - Solution

## Real-world grounding

**CWE-602 (Client-Side Enforcement of Server-Side Security)** and **CWE-807 (Reliance on
Untrusted Inputs in a Security Decision).** The console's rule is "a human traces this by hand."
Nothing on the server can tell a hand from a script. It receives a list of coordinates, and
input-automation tools make the browser produce exactly the same trusted events a hand does.
The same mistake shows up in real systems: CAPTCHAs and "human interaction" gates that read
mouse telemetry, and games that trust client input.

## How the service works

- `GET /` serves a 600x600 canvas with a planet at (300, 300).
- On load, and after each attempt, the page calls `POST /api/round` and gets a single-use
  `round_id` plus a `nonce`.
- The page records one pointer stroke as `[x, y, t_ms]` points. It **discards any event with
  `isTrusted == false`**, so `dispatchEvent(new PointerEvent(...))` from the DevTools console
  aborts with "Synthetic input detected."
- On release it sends `POST /api/transmit` with `round_id`, the points, and
  `sig = HMAC-SHA256(key=nonce, msg="x.xx,y.yy,t;...")`. The signer is plain JS in
  `/static/nav.js`.
- The server checks the signature, the timestamps (start at 0, never decrease, at least 400 ms,
  no longer than the time since the round was issued), then fits a least-squares circle and
  requires all of the following:
  - radius >= 120 px, center within 10% of R from the planet
  - one full loop (>= 357 deg swept), no reversals, no gap > 12 deg between samples
  - **circularity = 100 * (1 - max|r_i - R| / R) >= 99.5%**

A careful human scores around 94-98%. Worst-case wobble on a 200 px loop is several pixels, and
99.5% allows about 1 px. Measured locally: a simulated "very steady" hand (1.2% + 0.6% low-frequency
wobble plus 1 px jitter) scored 97.96%. A scripted loop with integer pixel coordinates at
R = 150 scored 99.62%. An exact scripted loop scores 100%.

## Intended solve: let a script drive the mouse

1. Open the page and try a few loops by hand. The best you'll get is high 90s.
2. Read `/static/nav.js`. The stroke comes from pointer events, and synthetic (`isTrusted`
   false) events are rejected, so the console shortcut doesn't work.
3. Drive real input instead. Any of these produce trusted events:
   - Playwright / Puppeteer / Selenium `page.mouse.move` (CDP `Input.dispatchMouseEvent`)
   - OS-level cursor control: pyautogui, AutoHotkey, xdotool
4. Trace a circle centered on the planet (the canvas center) with radius ~150-250 px, one
   sample per degree or so, taking at least half a second, then release. The panel shows
   `Orbit locked` and the flag.

Reference: `solve.py` (Playwright, ~1 s run):

```
pip install -r requirements.txt
python -m playwright install chromium        # or use --channel msedge / chrome
python solve.py http://<challenge-host>:8080
```

## Alternate solve: skip the page

Reproduce the page's request yourself. Get a round, build the points, compute
`HMAC-SHA256(nonce, canonical(points))` where canonical is `"%.2f,%.2f,%d"` joined by `;`.
Wait at least as long as your last timestamp, then POST it. This needs reading the signer in
`nav.js`, so it takes more work than driving the mouse, but it's equally valid. Patching
`nav.js` with DevTools Local Overrides to drop the `isTrusted` check, then dispatching events
from the console, also works.

## What doesn't work

- Dispatching `PointerEvent`/`MouseEvent` from the console without patching the page (rejected
  client-side as synthetic).
- Replaying an old request (rounds are single-use).
- Editing the points without re-signing (`Telemetry checksum mismatch`).
- A tiny or off-center circle (radius and center checks).
