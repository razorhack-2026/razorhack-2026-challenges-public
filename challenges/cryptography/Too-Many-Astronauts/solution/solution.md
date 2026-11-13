# Too Many Astronauts in the Station

**Category:** Cryptography
**Difficulty:** Hard
**Author:** Lt. Niko Copernicus

## Competitor experience

The competitor-facing story and crew list are in `../README.md` and `../challenge.yml`.
Participants visit the nine listed crew members, played by GMs, to collect nine
ciphertext/public-key handouts. There are no CTFd downloads and no live service.
Participants can obtain the full set directly from the GMs; cross-team sharing is
not required.

## GM delivery

The nine `src/handout-NN.txt` files are the participant handouts. Each contains only
`C`, `e`, and `n`. Give each crew member one distinct handout and record the
crew-character-to-handout assignment before the event. Every team must be able
to collect the same complete set. The matching files in `solution/pub_keys/`
are the reference solver's copies of those handouts.

Only distribute the individual handout files. Keep `plain.txt`, the generator,
`publishedFactors.pkl`, challenge metadata, and this solution private.

## Intended solution (GM-only)

1. Collect all nine ciphertexts and their corresponding RSA public keys.
2. Observe that all keys use exponent `e = 9` and encrypt the same unpadded message
   under different, pairwise-coprime moduli.
3. Apply the Chinese Remainder Theorem to recover the message's ninth power.
4. Take the exact integer ninth root and decode the resulting bytes to recover
   the message and flag.

The reference solver prints `True` when the recovered value is a perfect ninth
power, then prints the decoded message. The flag must match `flags[0]` in
`../challenge.yml` exactly.

# Solve Script

- Run `python solution.py` from within the `solution/` directory.
