# MED BAY: Keyboard Warrior — GM Solution

The web app keeps the level, clock, and single-use attempt nonce in server-side session state. The browser is only a client for the assessment API.

1. Start an assessment and request each level from `/api/level`.
2. The prompt in the response contains zero-width formatting characters on the final level. Remove those characters before submitting the text.
3. Submit the exact underlying prompt with its current nonce. Re-request the level after a failed attempt to get a fresh nonce and restart the clock.
4. Repeat through all four levels. The fourth prompt does not contain the flag. Only a passing final submission marks the assessment complete and returns the configured flag in the final JSON response. The browser then displays the “Typing test completed” screen with the clearance report.

`solve.py` automates the API flow. `test_challenge.py` checks session handling, timing, accuracy, replay protection, final-level behavior, and flag withholding.

Configured flag: `flag{l1ghtn1ng_f4st}`
