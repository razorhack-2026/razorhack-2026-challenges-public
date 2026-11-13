# GM verification: Can you hear me?

Run commands from challenges/forensics/comm/ using Python 3.12.

~~~sh
python -m pip install -r solution/requirements.txt
~~~

~~~sh
python solution/verify.py
~~~

The verifier captures solver output, compares the recovered flag exactly with challenge.yml, and reports only PASS/FAIL. Do not paste direct solver output into logs, PRs, or public documentation. Static solvers use only dist/; service solvers use the local exposed interface.

The solver reconstructs the image in a temporary directory, then uses local OCR to recover the painted token. OCR is offline; no challenge material is uploaded. A recovered image may be retained with --image PATH for GM inspection.

## Reference approach (GM only)

File challenge. Players get `static_loop.wav`, which is noise. The payload is not
text: `src/image.png` is hidden in the LSB of every 7th sample.

Extract those bits, write them to a file, and open the PNG. The flag is painted
on the image.

Replace `challenges/forensics/comm/src/image.png` and re-run the generator to change the
still. Keep the painted flag in sync with `challenge.yml`. The WAV is large
(~33 MB) because of the 7-sample stride.

## Deployment

Metadata uses the repository's uniform scoring and stays hidden. Import this folder independently with ctfcli; scoreboard unlock gates are omitted so separate PRs do not require a particular merge order. For live services, replace localhost connection information only when the event endpoint is assigned.
