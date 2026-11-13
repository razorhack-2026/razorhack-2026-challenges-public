# GM verification: THRUST: Burn Schedule

Run commands from challenges/rev/thrust/ using Python 3.12.

~~~sh
python -m pip install -r solution/requirements.txt
~~~

~~~sh
python solution/verify.py
~~~

The verifier captures solver output, compares the recovered flag exactly with challenge.yml, and reports only PASS/FAIL. Do not paste direct solver output into logs, PRs, or public documentation. Static solvers use only dist/; service solvers use the local exposed interface.

The reference script statically decodes the supplied ELF's transformed data, so verification also works on hosts that cannot execute Linux binaries.

## Reference approach (GM only)

File challenge. Players reverse `thruster_ctl`. The 16-byte authorization code is
XOR'd with `0x42` and compared against a constant; the flag is stored the same
way. The code is `BURN_microbot_7!`.

Rebuild with `bash challenges/rev/thrust/src/build.sh` after changing the hidden
bytes. Keep the printed flag in sync with `challenge.yml`.

## Deployment

Metadata uses the repository's uniform scoring and stays hidden. Import this folder independently with ctfcli; scoreboard unlock gates are omitted so separate PRs do not require a particular merge order. For live services, replace localhost connection information only when the event endpoint is assigned.
