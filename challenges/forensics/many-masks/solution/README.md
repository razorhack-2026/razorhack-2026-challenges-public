# Many Masks

**Category:** Forensics  
**Difficulty:** Hard  
**Author:** Jebediah Kerman  

## Description

Salvage pulled one file off the derelict's data core. Our tooling says it is an image and
refuses to discuss it further. The caption it displays starts something it never finishes.

## Files Provided

- `artifact.png`

## Flag

`flag{0n3_f1l3_we4r5_m4ny_m45k5}`

## Concept

`artifact.png` is simultaneously a valid **PNG image**, a valid **HTML page**, and a valid
**ZIP archive** — the *same bytes*, read by three different parsers. Each identity carries one
third of the flag.

| Identity | Opened with | Piece |
|---|---|---|
| PNG | any image viewer | `flag{0n3_f1l3_` |
| HTML | a web browser | `we4r5_m4ny_` |
| ZIP | any archive tool | `m45k5}` |

No crypto, no trivia. The challenge tests one idea: a file's extension, and what `file` reports,
is only *the first landmark a parser happens to find*.

## Why it works — format anchoring

Each format anchors on a different region and ignores the rest:

- **PNG** anchors at **offset 0** (`89 50 4E 47`), then walks length-prefixed chunks. A chunk
  whose type begins with a lowercase letter is *ancillary* and is skipped by any decoder that
  does not recognise it. The image ends at `IEND`.
- **HTML** has **no magic bytes at all**. A browser renders `<tags>` wherever they appear and
  treats surrounding binary as inert text.
- **ZIP** anchors at the **end of file**, scanning backward for the End Of Central Directory
  record (`PK\x05\x06`), then following offsets to the entries.

PNG needs the start, ZIP needs the end, HTML needs neither — so all three coexist.

### This build is nested, not appended — the Hard-tier detail

A naive polyglot concatenates `PNG + HTML + ZIP`. That works, but `binwalk -e` or `foremost`
carve the trailing data straight out, which drops it to Medium.

This build hides the HTML and ZIP **inside PNG ancillary chunks**:

```
IHDR -> htMl{ <html>...</html> } -> IDAT -> zpDt{ PK...EOCD } -> IEND
```

Structurally the file is **one valid PNG with nothing after `IEND`**, so there is no trailing
blob to carve. The ZIP still validates because `unzip` locates the EOCD by scanning backward
from EOF and does not care that it sits inside a PNG chunk, and because the EOCD
**comment-length** field is patched to `16` so the 16 bytes that follow it (the `zpDt` CRC plus
the 12-byte `IEND` chunk) are swallowed as the archive comment.

## Solution

**Step 1 — look at it.** It is an image reading `flag{0n3_f1l3_`. The flag is **unterminated**:
it opens with `flag{` and never closes. That is the only nudge that more is hidden.

**Step 2 — notice the size.** A 720x240 image showing one line of text is ~8.5 KB. Chunky.

**Step 3 — look inside.**

```
$ file artifact.png
artifact.png: PNG image data, 720 x 240, 8-bit/color RGB      # only the FIRST identity

$ python -c "b=open('artifact.png','rb').read(); print('<html>', b.find(b'<html>')); print('PK', b.find(b'PK\x03\x04'))"
<html> 56
PK ...
```

Finding `<html>` and a ZIP signature *inside* something `file` calls a PNG is the aha.

**Step 4 — extract the other two faces.** Same bytes, different parser:

```
$ cp artifact.png x.zip && unzip x.zip
  inflating: note.txt        ->  m45k5}

$ cp artifact.png x.html && open x.html
  the page renders:  we4r5_m4ny_
```

**Step 5 — assemble.** The `flag{...}` delimiters fix the order; nothing is labelled.

```
flag{0n3_f1l3_   (PNG  - begins with 'flag{')
we4r5_m4ny_      (HTML - the middle)
m45k5}           (ZIP  - ends with '}')
```

## Answer key

- Flag: `flag{0n3_f1l3_we4r5_m4ny_m45k5}`
- Piece A, PNG image caption: `flag{0n3_f1l3_`
- Piece B, HTML `<b>` element: `we4r5_m4ny_`
- Piece C, ZIP entry `note.txt`: `m45k5}`
- Order comes from the flag delimiters, not from any label.

**Author verification (2026-08-23):** re-checked against the shipped `dist/artifact.png` with
real tools — PIL opens it as a 720x240 RGB PNG, chunk order is
`IHDR, htMl, IDAT, zpDt, IEND` with nothing after `IEND`, `<html>` is intact at offset 56, and
`unzip` inflates `note.txt`. All three pieces recovered.

## Notes for organisers

- **The `unzip` "extra bytes at beginning" warning is expected** — it is the PNG data preceding
  the ZIP. It doubles as a fair breadcrumb that the file is a polyglot. Leave it.
- **No labels remain.** Earlier drafts printed `fragment[0]` / `PARTIAL 1/3`; these were removed
  so players must discover there are three pieces and infer the order. If it plays too hard in
  testing, the cheapest hint is a description line like *"one file, three faces"* — note the
  current description already leans that way with the three-manifest-entries framing.
- **Difficulty comes from format literacy**, not obscure knowledge. Every step is verifiable
  with off-the-shelf tools (`file`, `binwalk`, a hex editor, `unzip`, a browser), which keeps it
  fair for a Hard.

## Open items for review

- [ ] Full human playtest: rename to `.zip` / `.html` on a clean machine and confirm both open
      as expected outside the author's environment.
- [ ] Decide whether to keep the `unzip` warning or suppress it, which would require padding the
      EOCD comment to end exactly at EOF.
