# Pulsar Dropbox

**Category:** Forensics  
**Difficulty:** Medium  
**Author:** Jebediah Kerman  

## Description

The file share went down again, so Dr. Vance's colleague did what any reasonable person does
under deadline: mailed the observation over in pieces. Then someone locked the last attachment
"for safety" and went on leave.

## Files Provided

- `inbox.mbox`

## Flag

`flag{IC4nTB3liev3th1s1sR34LTechNologY!}`

## Solution

Two stages: reassemble a file split across a reply thread, then use what it shows you as a
decryption key.

### Stage 1 — find the real thread

`inbox.mbox` holds **19 emails in 4 threads**. Three are decoys (IT maintenance, payroll,
calibration logs) and some carry benign non-hex attachments such as `.pdf` and `.log` as bait.
The real thread is the long exchange between **Dr. Elena Vance** and **M. Okafor**, subject
**"the clip"**, whose `.txt` attachments contain hex.

Only one thread's attachments rebuild into a valid file, so a player who blindly concatenates
every attachment in the mailbox fails.

### Stage 2 — recover the order

This is the primary skill gate. `Date` headers are randomised across a multi-day window and the
attachment filenames are random tokens, so **sorting by date or filename fails by design**. The
only correct ordering is the `In-Reply-To` / `References` chain:

- **Root** — the message with no `In-Reply-To`. Its fragment starts `47 49 46 38 39 61`
  (`GIF89a`), the file header.
- **Leaf** — the fragment ending `00 3B`, the GIF trailer.

Walk the chain root to leaf for the 10 fragments in order.

### Stage 3 — rebuild the payload

Concatenate the 10 hex fragments in chain order and un-hex. In CyberChef, recipe `From Hex`
with delimiter `Auto`.

Result: **618,428 bytes**, sha256
`c0b20f4bfb35c9e771ccc30b92992c45b4127a70b94047218bd05a0bf5235dff`.

It is an animated GIF of a star chart labelling **`PSR B1937+21`**, with a spinning-pulsar
inset.

### Stage 4 — the catalogue lookup

Look `PSR B1937+21` up in the public **ATNF Pulsar Catalogue**: it is `PSR J1939+2134`, in the
constellation **Vulpecula**. That word is the stage-2 key. This is the only step that requires
anything outside the mailbox.

### Stage 5 — decrypt

The real thread's 11th and final message carries `observation.enc`, a 39-byte blob: the flag
under repeating-key XOR.

```
Input:  observation.enc   (loaded as a FILE, not pasted — see pitfall below)
Recipe: XOR   Key = Vulpecula   (type: UTF8, scheme: Standard)
```

Equivalent, from the raw ciphertext:

```
hex:    30190d171e2a36580f02375f1c0c06035f153e441f41163146582d02100f182b0c1903060f5411
base64: MBkNFx4qNlgPAjdfHAwGA18VPkQfQRYxRlgtAhAPGCsMGQMGD1QR
```

`From Hex` / `From Base64`, then XOR with key `Vulpecula` (UTF8).

## Answer key

- Inbox: 19 emails, 4 threads, exactly **1 thread is hex-rebuildable**.
- Real thread: 11 emails = 10 hex fragments + `observation.enc`. 8 decoy emails across 3 threads.
- Rebuilt GIF: 618,428 bytes, sha256 `c0b20f4b…5235dff`, header `GIF89a`, trailer `00 3B`.
- Pulsar `PSR B1937+21` = `J1939+2134` → constellation **Vulpecula**.
- Stage 2: 39-byte ciphertext, XOR key `Vulpecula` → the flag above.

**Author verification (2026-08-23):** solved end to end from the shipped `dist/inbox.mbox`;
rebuilt GIF sha256 matched the value above byte for byte and the flag recovered exactly as it
appears in `challenge.yml`.

## Known pitfall — the `0x0D` / CRLF trap

The ciphertext contains a **`0x0D` (carriage return) at offset 2**. If a player handles
`observation.enc` as *text* at any point — copy-pasting it, piping it through a text-mode shell,
opening and re-saving it in an editor — that byte expands to `0x0D 0x0A`. The inserted byte
shifts everything after it out of alignment with the key, so the decrypt yields `fla` followed
by garbage and **the correct key looks wrong**.

Correct handling is to load the attachment as raw bytes (CyberChef's file loader, `xxd`,
`open(..., "rb")`). The competitor `README.md` carries a non-spoiling nudge about treating
attachments as raw bytes, which is the intended mitigation.

Note the same class of bug bit the artifact itself: `mailbox.mbox.add()` writes CRLF line
endings, and a CRLF mbox makes Thunderbird import the whole file as a single message. The
generator normalises to Unix-LF, and this branch adds `*.mbox binary` to `.gitattributes` so
`core.autocrlf` cannot undo that on checkout.

## Design notes

- **Ordering is the gate.** Dates scrambled, filenames randomised; only the reply chain gives
  the correct order.
- **Both file ends are content-anchorable.** The payload was migrated from MP4 to GIF precisely
  so the final fragment is verifiable — GIF has both a magic header and a trailer, where MP4 has
  no footer magic and left the last chunk unidentifiable.
- **No hand-holding.** Message bodies are ordinary thread chatter; nothing states that this is a
  split file or how to reassemble it.
- **Self-validating stage 2.** The plaintext is a readable `flag{…}`, so a wrong key produces
  obvious garbage.

## Open items for review

- [ ] **Spoiler check:** the star chart prints the word `Vulpecula` on it, which can hand a
      player the stage-2 key without the ATNF lookup. Decide whether to crop it out or accept
      it — this is the one open design question on this challenge.
- [ ] Optional hardening: regenerate so the ciphertext contains no `0x0D`/`0x0A`, removing the
      CRLF trap entirely rather than documenting around it.
