# GM verification: Wrong Direction

Run commands from challenges/misc/nav/ using Python 3.12.

~~~sh
python -m pip install -r solution/requirements.txt
~~~

~~~sh
python solution/verify.py
~~~

The verifier captures solver output, compares the recovered flag exactly with challenge.yml, and reports only PASS/FAIL. Do not paste direct solver output into logs, PRs, or public documentation. Static solvers use only dist/; service solvers use the local exposed interface.

## Reference approach (GM only)

File challenge. Players download `nav_log.txt` and peel encodings until they get
coordinates.

The real fix is base64 in segment E. Decode it and submit it verbatim:

```
flag{n4v_<coordinates>}
```

To change the destination, edit `COORD` in `challenges/misc/nav/src/generate.py`,
re-run the generator, and copy the printed flag into `challenge.yml`.

## Deployment

Metadata uses the repository's uniform scoring and stays hidden. Import this folder independently with ctfcli; scoreboard unlock gates are omitted so separate PRs do not require a particular merge order. For live services, replace localhost connection information only when the event endpoint is assigned.
