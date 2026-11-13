#!/usr/bin/env python3
"""
Five By Five - RazorPower Co. break-room word game, live service.

A Wordle clone, 5-letter cyber vocabulary, one random word per session. The
page gives you exactly one visible guess: submit it, see the colored
feedback, and the input locks -- "you've used your one attempt." That lock
is entirely client-side (see the page's own <script> below).

A session works like this: on page load, the page's JS calls
GET /api/session once, which allocates a fresh random secret word and a
session_id and hands the id back. The page stores that id in a JS variable
and sends it along with its one /api/guess call. Nothing about any of this
is tied to the browser, a cookie, or the page being "open" -- a session_id
is just a string the server will keep honoring forever, for as many
/api/guess calls as you like, whether or not the page that first fetched it
is ever reloaded again. Capture that one id and you don't need the page at
all after that; score your own guesses against it directly, as many times
as you want, with full per-letter feedback every time -- exactly like real
Wordle.

Real grounding: CWE-602, Client-Side Enforcement of Server-Side Security --
trusting a UI-level restriction (one guess, tied to "using the page") that
the actual API was never built to enforce once you hold the session id it
handed out.

_score() is the same duplicate-letter-aware Wordle/Mastermind scoring as
Daily Uplink's oracle (challenges/misc/Daily_Uplink/src/uplink/app.py).

FLAG comes from the environment - see docker-compose.yml. Secret words come
from WORD_BANK below, one chosen at random per session.
"""
import os
import re
import secrets
import random

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

FLAG = os.environ["WORDLE_FLAG"]
ALPHABET = os.environ.get("WORDLE_ALPHABET", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
SECRET_LEN = 5

WORD_BANK = [
    "PROXY", "TOKEN", "CACHE", "WORMS", "SPOOF",
    "PHISH", "VIRUS", "CRYPT", "AUDIT", "PATCH",
    "LEAKS", "VAULT", "SHELL", "NONCE", "STACK",
    "LOGIN", "SNIFF", "ROUTE", "ADMIN", "TRACE",
]
assert all(len(w) == SECRET_LEN for w in WORD_BANK), "every WORD_BANK entry must be 5 characters"
assert all(c in ALPHABET for w in WORD_BANK for c in w), "WORD_BANK entries must be drawn from WORDLE_ALPHABET"

_GUESS_RE = re.compile(r"^[%s]+$" % re.escape(ALPHABET))

# session_id -> secret word. In-memory is fine for this challenge: one
# process, no persistence needed, and a session's secret never changes
# once allocated.
SESSIONS = {}

HOME_PAGE = """
<!doctype html>
<html>
<head>
  <title>Five By Five - RazorPower Co. Break Room</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --color-tone-1: #ffffff;
      --color-tone-2: #818384;
      --color-tone-3: #565758;
      --color-tone-4: #3a3a3c;
      --color-tone-7: #121213;
      --green: #538d4e;
      --yellow: #b59f3b;
      --absent: #3a3a3c;
    }

    * {
      box-sizing: border-box;
    }

    html, body {
      height: 100%;
    }

    body {
      font-family: "nyt-franklin", Arial, "Helvetica Neue", Helvetica, sans-serif;
      background: var(--color-tone-7);
      color: var(--color-tone-1);
      margin: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    header {
      width: 100%;
      max-width: 500px;
      border-bottom: 1px solid var(--color-tone-4);
      padding: 16px 0;
      text-align: center;
    }

    header h1 {
      margin: 0;
      font-size: 2.25rem;
      font-weight: 700;
      letter-spacing: 0.01em;
    }

    p.sub {
      color: var(--color-tone-2);
      font-size: 0.95rem;
      margin: 10px 0 0;
    }

    p.tagline {
      color: var(--color-tone-3);
      font-size: 0.75rem;
      font-style: italic;
      margin: 6px 0 0;
    }

    main {
      width: 100%;
      max-width: 500px;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px;
    }

    .board {
      display: grid;
      grid-template-columns: repeat(5, 62px);
      gap: 5px;
      margin: 8px 0 28px;
    }

    .tile {
      width: 62px;
      height: 62px;
      border: 2px solid var(--color-tone-4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--color-tone-1);
      background: var(--color-tone-7);
      user-select: none;
    }

    .tile.filled {
      border-color: var(--color-tone-3);
    }

    .tile.flip {
      animation: flip 0.5s ease forwards;
    }

    @keyframes flip {
      0% { transform: rotateX(0); }
      50% { transform: rotateX(90deg); }
      100% { transform: rotateX(0); }
    }

    .tile.hit {
      background: var(--green);
      border-color: var(--green);
      color: #fff;
    }

    .tile.present {
      background: var(--yellow);
      border-color: var(--yellow);
      color: #fff;
    }

    .tile.absent {
      background: var(--absent);
      border-color: var(--absent);
      color: #fff;
    }

    .hidden-input {
      position: absolute;
      opacity: 0;
      height: 1px;
      width: 1px;
      border: none;
      padding: 0;
      margin: 0;
      overflow: hidden;
    }

    #msg {
      margin-top: 18px;
      font-size: 0.95rem;
      font-weight: 600;
      min-height: 1.3rem;
      text-align: center;
    }

    #hint {
      margin-top: 4px;
      font-size: 0.8rem;
      color: var(--color-tone-2);
      min-height: 1.1rem;
      text-align: center;
    }

    .keyboard {
      margin-top: 28px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      width: 100%;
      max-width: 480px;
    }

    .kb-row {
      display: flex;
      gap: 6px;
      justify-content: center;
    }

    .key {
      flex: 1;
      min-width: 0;
      height: 46px;
      border: none;
      border-radius: 4px;
      background: var(--color-tone-2);
      color: var(--color-tone-1);
      font-weight: 700;
      font-size: 0.85rem;
      text-transform: uppercase;
      font-family: inherit;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      padding: 0 4px;
      user-select: none;
    }

    .key.wide {
      flex: 1.6;
      font-size: 0.65rem;
      letter-spacing: 0.02em;
    }

    .key:active {
      opacity: 0.7;
    }

    .key.hit {
      background: var(--green);
    }

    .key.present {
      background: var(--yellow);
    }

    .key.absent {
      background: var(--color-tone-4);
      color: #808080;
    }
  </style>
</head>
<body>
  <!-- RazorPower Co. Security Notice: this terminal's one-attempt policy
       is enforced, audited, and fully tamper-proof. Nothing further to
       see here. -->
  <header>
    <h1>Five By Five</h1>
    <p class="tagline">Single-attempt security, guaranteed unbreakable.</p>
  </header>

  <main>
    <div class="board" id="grid">
      <div class="tile" id="t0"></div>
      <div class="tile" id="t1"></div>
      <div class="tile" id="t2"></div>
      <div class="tile" id="t3"></div>
      <div class="tile" id="t4"></div>
    </div>

    <input id="hiddenInput" class="hidden-input" maxlength="5" autocomplete="off"
           autocapitalize="characters" autocorrect="off" spellcheck="false">

    <div id="msg"></div>
    <div id="hint">Type your guess, then press Enter.</div>

    <div class="keyboard" id="keyboard">
      <div class="kb-row">
        <button class="key" data-key="Q">Q</button>
        <button class="key" data-key="W">W</button>
        <button class="key" data-key="E">E</button>
        <button class="key" data-key="R">R</button>
        <button class="key" data-key="T">T</button>
        <button class="key" data-key="Y">Y</button>
        <button class="key" data-key="U">U</button>
        <button class="key" data-key="I">I</button>
        <button class="key" data-key="O">O</button>
        <button class="key" data-key="P">P</button>
      </div>
      <div class="kb-row">
        <button class="key" data-key="A">A</button>
        <button class="key" data-key="S">S</button>
        <button class="key" data-key="D">D</button>
        <button class="key" data-key="F">F</button>
        <button class="key" data-key="G">G</button>
        <button class="key" data-key="H">H</button>
        <button class="key" data-key="J">J</button>
        <button class="key" data-key="K">K</button>
        <button class="key" data-key="L">L</button>
      </div>
      <div class="kb-row">
        <button class="key wide" data-key="ENTER">Enter</button>
        <button class="key" data-key="Z">Z</button>
        <button class="key" data-key="X">X</button>
        <button class="key" data-key="C">C</button>
        <button class="key" data-key="V">V</button>
        <button class="key" data-key="B">B</button>
        <button class="key" data-key="N">N</button>
        <button class="key" data-key="M">M</button>
        <button class="key wide" data-key="BACKSPACE">&larr;</button>
      </div>
    </div>
  </main>

  <script>
    let used = false;
    let sessionId = null;

    async function initSession() {
      const res = await fetch("/api/session");
      const data = await res.json();
      sessionId = data.session_id;
    }
    initSession();

    const guessInput = document.getElementById("hiddenInput");
    const grid = document.getElementById("grid");

    function focusInput() {
      if (!used) guessInput.focus();
    }
    focusInput();
    grid.addEventListener("click", focusInput);
    document.body.addEventListener("click", focusInput);

    function renderTiles() {
      const clean = guessInput.value;
      for (let i = 0; i < 5; i++) {
        const tile = document.getElementById("t" + i);
        tile.textContent = clean[i] || "";
        tile.classList.toggle("filled", i < clean.length);
      }
    }

    guessInput.addEventListener("input", () => {
      guessInput.value = guessInput.value.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 5);
      renderTiles();
    });

    async function trySubmit() {
      if (used) return;
      if (!sessionId) {
        document.getElementById("msg").textContent = "Session still loading, try again in a moment.";
        return;
      }
      const guess = guessInput.value;
      if (guess.length !== 5) {
        document.getElementById("msg").textContent = "Guess must be 5 characters.";
        return;
      }

      const res = await fetch("/api/guess", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({session_id: sessionId, guess})
      });
      const data = await res.json();

      if (data.error) {
        document.getElementById("msg").textContent = data.error;
        return;
      }

      used = true;
      guessInput.disabled = true;
      guessInput.blur();
      document.getElementById("hint").textContent = "";

      const rank = {hit: 3, present: 2, absent: 1};
      const bestForKey = {};
      data.feedback.forEach((f) => {
        if (!bestForKey[f.char] || rank[f.result] > rank[bestForKey[f.char]]) {
          bestForKey[f.char] = f.result;
        }
      });
      Object.keys(bestForKey).forEach((ch) => {
        const key = document.querySelector('.key[data-key="' + ch + '"]');
        if (key) key.classList.add(bestForKey[ch]);
      });

      const STAGGER_MS = 180;
      const FLIP_MS = 500;
      data.feedback.forEach((f, i) => {
        const tile = document.getElementById("t" + i);
        tile.style.animationDelay = (i * STAGGER_MS) + "ms";
        tile.classList.add("flip");
        setTimeout(() => {
          tile.textContent = f.char;
          tile.classList.add(f.result);
        }, i * STAGGER_MS + FLIP_MS / 2);
      });

      setTimeout(() => {
        if (data.solved) {
          document.getElementById("msg").textContent = "Solved: " + data.flag;
        } else {
          document.getElementById("msg").textContent = "You've used your one attempt.";
        }
      }, (data.feedback.length - 1) * STAGGER_MS + FLIP_MS);
    }

    guessInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") trySubmit();
    });

    document.getElementById("keyboard").addEventListener("click", (e) => {
      const btn = e.target.closest(".key");
      if (!btn || used) return;
      const k = btn.dataset.key;
      if (k === "ENTER") {
        trySubmit();
      } else if (k === "BACKSPACE") {
        guessInput.value = guessInput.value.slice(0, -1);
        renderTiles();
      } else if (guessInput.value.length < 5) {
        guessInput.value += k;
        renderTiles();
      }
      focusInput();
    });
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HOME_PAGE)


@app.route("/api/session")
def new_session():
    session_id = secrets.token_hex(8)
    SESSIONS[session_id] = random.choice(WORD_BANK)
    return jsonify({"session_id": session_id})


def _score(guess: str, secret: str):
    """Classic Wordle/Mastermind-style scoring with correct duplicate handling.

    Same two-pass multiset accounting as Daily Uplink's oracle: a guess is
    free to repeat characters even though WORD_BANK entries do not.
    """
    n = len(guess)
    result = [None] * n
    secret_remaining = {}

    for i, (g, s) in enumerate(zip(guess, secret)):
        if g == s:
            result[i] = "hit"
        else:
            secret_remaining[s] = secret_remaining.get(s, 0) + 1

    for i, g in enumerate(guess):
        if result[i] is not None:
            continue
        if secret_remaining.get(g, 0) > 0:
            result[i] = "present"
            secret_remaining[g] -= 1
        else:
            result[i] = "absent"
    return result


@app.route("/api/guess", methods=["POST"])
def guess():
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")
    g = body.get("guess", "")

    if session_id not in SESSIONS:
        return jsonify({"error": "unknown or missing session_id"}), 404

    if not isinstance(g, str):
        return jsonify({"error": f"guess must be a {SECRET_LEN}-character string"}), 400
    g = g.upper()
    if len(g) != SECRET_LEN:
        return jsonify({"error": f"guess must be a {SECRET_LEN}-character string"}), 400
    if not _GUESS_RE.match(g):
        return jsonify({
            "error": f"guess must only use characters from '{ALPHABET}'"
        }), 400

    secret = SESSIONS[session_id]
    outcomes = _score(g, secret)
    feedback = [
        {"pos": i, "char": c, "result": outcomes[i]} for i, c in enumerate(g)
    ]
    solved = g == secret

    payload = {"feedback": feedback, "solved": solved}
    if solved:
        payload["flag"] = FLAG
    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
