# Are We There Yet? — printable share cards (GM-only)

Physical props for the `Are We There Yet?` challenge. Each card is a wall/venue handout; the **share value lives on the NFC tag**, not on the paper (by default).

## Files

| File | What it is |
|---|---|
| `make_share_cards.py` | Generator (standard library only, no pip installs) |
| `share-01.pdf`, `share-03.pdf`, `share-06.pdf`, `share-07.pdf`, `share-08.pdf` | The five wall cards, US Letter |
| `all-shares.pdf` | The generated wall cards, one per page |
| `nfc_payloads.txt` | Exact text to write to each tag (GM-only, all nine shares) |
| `nfc_payloads.csv` | Same data plus a `suggested_placement` column |

Shares **2, 4, 5, 9** already have delivery locations in `../../solution/solution.md` (Lt. Rico Kopernicus, Flyer, Website, Davie Bowman), so they get **no wall card**. Only the five unlocated shares — **1, 3, 6, 7, 8** — are printed by default. Pass `--all` if you ever want cards for all nine.

Regenerate after any change to `../shares.txt`:

```sh
python3 make_share_cards.py                 # the five wall cards; value on tag only
python3 make_share_cards.py --include-value # same, plus printed value fallback
python3 make_share_cards.py --all           # cards for all nine shares
```

The script reads `../shares.txt` (source of truth), so it picks up threshold, modulus, and all nine share values automatically.

## Printing

- **US Letter**, portrait, **100% / actual size** (do not "fit to page" — the dashed circle is sized for the tag placement).
- Single-sided, colour if possible; it also reads fine in greyscale.
- Cardstock or a laminating pouch survives a weekend of handling; plain paper taped at all four corners is fine indoors.
- Do not print the `nfc_payloads.*` sheets for players.

## NFC tags

Write one tag per share, using the matching line from `nfc_payloads.txt`:

```text
1, 0x93c472d19327f95d33f48df3c5d828b6325af911d9971a9745efdd6e373116b0
2, 0x9d3e8928e8a015768d6e481684b263c1f0a7bc8c97fde969cc45892ab74f256c
...
```

Format is exactly `<share index>, <0x-prefixed hex value>` — the same shape the reference solver consumes. Field 1 is `x`, field 2 is `y`.

- Tag type: **NTAG213/215/216** (any NDEF Type-2 tag is fine; the payload is ~80 bytes, well under NTAG213's ~144-byte user memory).
- Record type: one **NDEF Text record** (`text/plain`, UTF-8), no extra records.
- Tools: "NFC Tools" (Android/iOS) or NXP "TagWriter"; write the payload text verbatim. The NFC tags were made permanently read-only, so verify each payload before locking (locking is irreversible).
- Test every tag with a real phone before taping: the phone should show the text, not a URL or a blank record.
- **Avoid metal.** Tags on metal desks/doors detune and may not read; use an anti-metal tag or a 5–10 mm foam/plastic spacer between tag and surface.
- Mount the tag **behind the centre of the dashed circle**, then tape/glue the card at its corners only. Taping over the tag is fine; taping over the whole front of the phone does not help and can interfere with some readers.

## Placement plan

The challenge says five shares are around the ship and four are "distributed in other ship systems and materials". The GM notes in `../../solution/solution.md` record the intended split; `nfc_payloads.csv` carries it in `suggested_placement`:

| Share | Suggested placement |
|---|---|
| 1 | wall / venue |
| 2 | crew member — Lt. Rico Kopernicus |
| 3 | wall / venue |
| 4 | material — flyer |
| 5 | material — website |
| 6 | wall / venue |
| 7 | wall / venue |
| 8 | wall / venue |
| 9 | crew member — Davie Bowman |

The five wall shares are therefore **1, 3, 6, 7, 8**. That is exactly what the script prints by default; use `--all` only if you decide to put the crew/material shares on paper as well. The tag payload sheet still covers all nine, because the crew and material handouts can use tags too.

Keep every card in a publicly accessible area, reachable without tools, ladders, or moving furniture — matching the disclaimer in `../../README.md`. If reaching a card needs any of that, it is in the wrong place.

## Fallback

If you are worried about tag failures (dead battery is not a thing, but damaged tags are), run with `--include-value`; the share value is printed in red under the modulus. That makes the tag optional but still keeps the narrative prop. Consider keeping **one** fallback card in the GM room rather than printing all nine with values.

## Verification

The values in `../shares.txt` were checked before generating these cards: every one of the 126 five-share combinations reconstructs the same constant term, and it matches the challenge flag in `../../challenge.yml`. Re-run that check whenever `shares.txt` changes, and re-verify the hidden physical placements actually add up to five distinct indices.

## Secrecy

These files are GM-only. `nfc_payloads.*` and any `--include-value` PDFs contain real share values; never copy them into `dist/`, a competitor-facing `README.md`, a PR, or any external service. The default cards contain only the public share index, modulus, and flavour text.
