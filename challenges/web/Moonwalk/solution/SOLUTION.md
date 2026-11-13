# Moonwalk — GM Solution

The server issues a round as rows of falling asteroids plus a key map for the four lanes. The browser displays this state; the server validates the full ordered response against a per-round nonce and deadline.

1. Start a mission and request a round. If the response is a countdown, wait until its timer expires and request the same round again.
2. For every row, find the lane containing the asteroid and use that lane's current key-map value.
3. Submit the ordered key list with the round nonce before its deadline.
4. Repeat for every round. The key map changes during later rounds; use the returned map each time.

`solve.py` automates the service flow. `test_challenge.py` covers sessions, nonce reuse, deadlines, input validation, countdowns, key rewiring, and completion.
