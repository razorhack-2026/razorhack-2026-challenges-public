# GM notes: Odd Pixel

The intended solve is to fetch `/api/challenge`, decode the returned PNG, find the one RGB triplet that differs from the common grey, and submit its coordinates before the five-second exposure window ends. Each challenge token is single-use, including after a wrong answer.

The server uses only the Python standard library. Run `docker compose up --build` from this folder to start it on port 8000 after setting `FLAG` in the service environment. The compose file requires the environment value and the source has no fallback flag.

Run `python solution/test_server.py` from this folder to start an ephemeral local service, solve it with the reference script, and check wrong, reused, expired, malformed, oversized, and unknown requests. The test emits only `PASS` or an error message and compares the recovered value with `challenge.yml`.

`test_playwright.js` is optional browser QA and requires Playwright with Chromium installed. It exercises the visible console as well as the API-focused verifier.
