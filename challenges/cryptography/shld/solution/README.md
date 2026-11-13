# GM verification: SHLD: Phase Inverter

Run commands from challenges/cryptography/shld/ using Python 3.12.

~~~sh
python -m pip install -r solution/requirements.txt
~~~

~~~sh
python solution/verify.py
~~~

The verifier captures solver output, compares the recovered flag exactly with challenge.yml, and reports only PASS/FAIL. Do not paste direct solver output into logs, PRs, or public documentation. Static solvers use only dist/; service solvers use the local exposed interface.

## Reference approach (GM only)

File challenge. Players get a hex ciphertext blob and a log that describes two
wraps. Undo AES-128-ECB first (key is `MD5("shield")`), then a Vigenere with key
`MICROBOT`. The flag is the `token=` field of the recovered plaintext.

To change the flag, edit `FLAG` in `challenges/cryptography/shld/src/generate.py`, re-run the
generator, and copy it into `challenge.yml`.

## Deployment

Metadata uses the repository's uniform scoring and stays hidden. Import this folder independently with ctfcli; scoreboard unlock gates are omitted so separate PRs do not require a particular merge order. For live services, replace localhost connection information only when the event endpoint is assigned.
