#!/usr/bin/env python3
"""
DRILL CONTAINMENT UNIT - hash mining challenge, level 3 (competitive).

Every team mines the same block. A new block with a fresh random nonce is
released every ROUND_SECONDS, aligned to the clock (:00, :30 for 30-minute rounds). The
first team to submit the nonce scores POINTS_PER_SOLVE, and the unit is sealed
for everyone until the next block is released. A wrong key locks out the whole
team, not just one connection.

On THE-DRILL this file is loaded by dcu_daemon.py, which hands every
connection to Competition.session(). For a quick local test in one terminal:
    python3 crypto_level3.py [state_dir]
"""

import grp
import hashlib
import json
import math
import os
import secrets
import sys
import threading
import time

CHARSET = "0123456789abcdef"
NONCE_LENGTH = 10
ROUND_SECONDS = 1800
LOCKOUT_SECONDS = 30
POINTS_PER_SOLVE = 1
FLAG = "flag{M0$t-V@1u!bl3-Ext4@ct04}"
GENESIS_PREV = "c0cf8e"  # first 6 characters of level 2's target hash
HISTORY_KEPT = 50
HISTORY_SHOWN = 10

# ANSI styling. Team colours are 256-colour codes 1-15 minus 7 and 8 (the greys);
# the top three ranks get gold, white and bronze.
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
TIME = "\033[38;5;159m"
BANNER_STYLE = "\033[1;30;48;5;229m"  # bold black on pale yellow (229)
TEAM_COLORS = [c for c in range(1, 16) if c not in (7, 8)]
RANK_COLORS = {1: 220, 2: 231, 3: 172}

BANNER = r"""
/////////////////////////////////////////////////////////
//                                                     //
//          D R I L L   C O N T A I N M E N T          //
//               U N I T   M O L E - 0 3               //
//                                                     //
/////////////////////////////////////////////////////////
"""


def sha256_hex(text):
    return hashlib.sha256(text.encode()).hexdigest()


def clock(ts):
    return time.strftime("%H:%M:%S", time.localtime(ts))


def duration(seconds):
    minutes, secs = divmod(max(0, int(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def paint(text, color):
    return f"\033[38;5;{color}m{text}{RESET}"


def timed(text):
    return f"{TIME}{text}{RESET}"


def bold(text):
    return f"{BOLD}{text}{RESET}"


def paint_rank(text, rank):
    return paint(text, RANK_COLORS[rank]) if rank in RANK_COLORS else text


def valid_format(key):
    return len(key) == NONCE_LENGTH and all(c in CHARSET for c in key)


def known_teams():
    try:
        return grp.getgrnam("teams").gr_mem
    except KeyError:
        return []


class Session:
    """One connected console. Broadcasts arrive from other threads, so writes are locked."""

    def __init__(self, write):
        self._write = write
        self._lock = threading.Lock()

    def send(self, text):
        with self._lock:
            try:
                self._write(text.encode())
            except OSError:
                pass

    def say(self, text=""):
        self.send(text + "\n")

    def prompt(self):
        self.send("ENTER KEY> ")

    def announce(self, text):
        """Interrupt whatever the player is typing, then give them a fresh prompt."""
        self.send(f"\n\n{text}\n\nENTER KEY> ")


class Competition:
    def __init__(self, state_dir):
        self.path = os.path.join(state_dir, "unit3.json")
        self.lock = threading.RLock()
        self.sessions = set()
        self.locked_until = {}
        self.state = self._load()
        self._rotate()
        threading.Thread(target=self._tick, daemon=True).start()

    # ---- state ---------------------------------------------------------

    def _load(self):
        try:
            with open(self.path) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {"scores": {}, "rounds": []}

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=1)
        os.replace(tmp, self.path)

    def team_color(self, team):
        """A team's colour, picked at random the first time it is seen (unused colours first)."""
        with self.lock:
            colors = self.state.setdefault("colors", {})
            if team not in colors:
                unused = [c for c in TEAM_COLORS if c not in colors.values()]
                colors[team] = secrets.choice(unused or TEAM_COLORS)
                self._save()
            return colors[team]

    def tag(self, team, text=None):
        """Team name (or other text) in the team's colour."""
        return paint(team if text is None else text, self.team_color(team))

    @property
    def round(self):
        return self.state["rounds"][-1]

    def _rotate(self):
        """Release a new block if the current one's window has closed. Returns the expired round, if any."""
        with self.lock:
            now = time.time()
            rounds = self.state["rounds"]
            if rounds and now < rounds[-1]["closes"]:
                return None
            prev = rounds[-1] if rounds else None
            used = {r["height"] for r in rounds}
            height = secrets.randbelow(1_000_000)
            while height in used:
                height = secrets.randbelow(1_000_000)
            block = f"DCU-07|SHAFT:K-6|BLOCK:{height:06d}|PREV:{prev['target'][:6] if prev else GENESIS_PREV}|NONCE:"
            nonce = "".join(secrets.choice(CHARSET) for _ in range(NONCE_LENGTH))
            rounds.append({
                "height": height,
                "block": block,
                "target": sha256_hex(block + nonce),
                "nonce": nonce,
                "released": now,
                "closes": now - now % ROUND_SECONDS + ROUND_SECONDS,
                "solved_by": None,
                "solved_at": None,
            })
            del rounds[:-HISTORY_KEPT]
            self._save()
            return prev or {}

    def _tick(self):
        while True:
            time.sleep(1)
            expired = self._rotate()
            if expired is None:
                continue
            lines = []
            if expired and not expired["solved_by"]:
                lines.append(f"{RED}[!!] BLOCK {expired['height']:06d} EXPIRED UNMINED. Its DIS was '{expired['nonce']}'.{RESET}")
            lines.append(f"{GREEN}[!!] NEW BLOCK RELEASED.{RESET}")
            self._broadcast("\n".join(lines) + "\n" + self.describe())

    def _broadcast(self, text, skip=None):
        with self.lock:
            targets = [s for s in self.sessions if s is not skip]
        for session in targets:  # sent outside the lock so a slow client can't stall the unit
            session.announce(text)

    # ---- views (also used by the console via dcu_daemon.py) -----------

    def describe(self):
        with self.lock:
            r = self.round
            lines = [
                f"BLOCK {r['height']:06d}  //  released {timed(clock(r['released']))}  //  new hash at {timed(clock(r['closes']))}",
                f"BLOCK_DATA   : {r['block']}{'?' * NONCE_LENGTH}",
                f"DEPOSIT_SHAPE: {BOLD}{r['target']}{RESET}",
            ]
            if r["solved_by"]:
                lines.append(f"[!] SEALED - mined by {self.tag(r['solved_by'])}. Next block at {timed(clock(r['closes']))}.")
            return "\n".join(lines)

    def status(self):
        with self.lock:
            r = self.round
            left = math.ceil(r["closes"] - time.time())
            nxt = f"NEW HASH {timed(clock(r['closes']))} (in {timed(duration(left))})"
            if r["solved_by"]:
                return f"SEALED by {self.tag(r['solved_by'])} | {nxt}"
            return f"ONLINE | {nxt}"

    def standings(self, *extra_teams):
        with self.lock:
            scores = self.state["scores"]
            teams = set(scores) | set(known_teams()) | set(extra_teams)
            return sorted(((scores.get(t, 0), t) for t in teams), key=lambda row: (-row[0], row[1]))

    def score_line(self, team):
        rows = self.standings(team)
        score = self.state["scores"].get(team, 0)
        rank = 1 + sum(1 for s, _ in rows if s > score)
        return (f"{self.tag(team)}  //  {self.tag(team, f'SCORE {score}')}  //  "
                f"{paint_rank(f'RANK {rank} of {len(rows)}', rank)}")

    def scoreboard(self):
        rows = self.standings()
        width = max([len("(in progress)")] + [len(t) for _, t in rows])
        out = [
            "",
            bold("  ======================================================"),
            bold("     DCU Mole-03  //  SCOREBOARD"),
            bold("  ======================================================"),
            bold(f"     RANK  {'TEAM':<{width}}  SCORE"),
        ]
        rank = 0
        for i, (score, team) in enumerate(rows):
            if i == 0 or score != rows[i - 1][0]:
                rank = i + 1
            out.append(f"     {paint_rank(f'{rank:>4}', rank)}  {self.tag(team, f'{team:<{width}}')}  {self.tag(team, f'{score:>5}')}")
        if not rows:
            out.append("     (no teams yet)")
        out += [
            "",
            bold(f"     BLOCK    RELEASED  {'SOLVED BY':<{width}}  SINCE RELEASE"),
        ]
        with self.lock:
            history = list(reversed(self.state["rounds"][-HISTORY_SHOWN:]))
        now = time.time()
        for r in history:
            if r["solved_by"]:
                who = self.tag(r["solved_by"], f"{r['solved_by']:<{width}}")
            elif r is history[0]:
                who = f"{'(in progress)':<{width}}"
            else:
                who = f"{'(unmined)':<{width}}"
            out.append(f"     {r['height']:06d}   {timed(clock(r['released']))}  {who}  {timed(duration(now - r['released']))}")
        return "\n".join(out) + "\n"

    # ---- play ----------------------------------------------------------

    def submit(self, team, key, session):
        """Returns (message, solved)."""
        with self.lock:
            now = time.time()
            r = self.round
            if r["solved_by"]:
                return f"[!] UNIT SEALED. Block {r['height']:06d} was mined by {self.tag(r['solved_by'])}. Next block at {timed(clock(r['closes']))}.", False
            wait = self.locked_until.get(team, 0) - now
            if wait > 0:
                return f"[!] CONSOLE LOCKED. {self.tag(team)} may try again in {timed(f'{math.ceil(wait)} seconds')}.", False
            digest = sha256_hex(r["block"] + key)
            if digest != r["target"]:
                self.locked_until[team] = now + LOCKOUT_SECONDS
                return (f"[-] WRONG KEY. '{key}' hashes to {digest[:16]}...\n"
                        f"[!] CONSOLE LOCKED for {timed(f'{LOCKOUT_SECONDS} seconds')} (all of {self.tag(team)})."), False
            r["solved_by"], r["solved_at"] = team, now
            scores = self.state["scores"]
            scores[team] = scores.get(team, 0) + POINTS_PER_SOLVE
            self._save()
            took = duration(now - r["released"])
            height, closes, score = r["height"], r["closes"], scores[team]
        self._broadcast(
            f"{GREEN}[!!] BLOCK {height:06d} MINED BY {self.tag(team)}{GREEN} in {took}.{RESET}\n"
            f"{GREEN}[!!] DCU Mole-03 is sealed. Next block releases at {clock(closes)}.{RESET}",
            skip=session,
        )
        return (f"\n[+] CORRECT KEY. Block {height:06d} mined in {timed(took)}.\n"
                f"[+] +{POINTS_PER_SOLVE} point. {self.tag(team)} score: {self.tag(team, str(score))}\n"
                f"[+] {FLAG}\n"
                f"[*] DCU Mole-03 is sealed for everyone until {timed(clock(closes))}."), True

    def session(self, reader, write, team):
        """Run one player's console. reader yields lines (bytes); write sends bytes."""
        s = Session(write)
        s.say()
        for line in BANNER.strip("\n").splitlines():
            s.say(f"{BANNER_STYLE}{line}{RESET}")
        s.say()
        s.say("DCU Mole-03 is the most profitable drill, but also the hardest to maneuver.")
        s.say("Every team attempts to control it, and only the best solution actually makes")
        s.say("the move: the first team to provide the correct DIS scores the point.")
        s.say(f"A new block is released every {timed(f'{ROUND_SECONDS // 60} minutes')}.")
        s.say("    sha256(BLOCK_DATA + DIS) == DEPOSIT_SHAPE")
        s.say(f"DIS (drill input sequence): {NONCE_LENGTH} characters from {CHARSET}")
        s.say(f"Wrong keys lock your whole team out for {timed(f'{LOCKOUT_SECONDS} seconds')}.\n")
        s.say(self.score_line(team))
        s.say(self.describe() + "\n")
        with self.lock:
            self.sessions.add(s)
        farewell = "\n[*] Session terminated."
        try:
            while True:
                s.prompt()
                line = reader.readline()
                if not line:
                    break
                key = line.decode(errors="replace").strip().lower()
                if not key:
                    continue
                if not valid_format(key):
                    s.say(f"[-] Invalid key format. Need exactly {NONCE_LENGTH} characters from: {CHARSET}")
                    continue
                message, solved = self.submit(team, key, s)
                s.say(message)
                if solved:
                    farewell = "[*] Returning to the access console."
                    break
        except OSError:
            pass
        finally:
            with self.lock:
                self.sessions.discard(s)
        s.say(farewell)


def main():
    competition = Competition(sys.argv[1] if len(sys.argv) > 1 else ".")

    def write(data):
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    try:
        competition.session(sys.stdin.buffer, write, os.environ.get("USER", "LOCAL"))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
