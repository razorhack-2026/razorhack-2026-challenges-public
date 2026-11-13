# Black Box Recovery — Solution

**GM-only. Contains the flag.**

Flag: `flag{the_black_box_kept_the_override_code}`

## Summary

`blackbox.img` is a 96 MB NTFS volume. The target, `LOGS/abort_log.txt` (MFT entry 82), is
deleted, **NTFS-compressed**, and its `$DATA` run list has been zeroed. The naive tools fail at
both levels:

- The run list is gone, so `icat` / `ntfsundelete` / Autopsy have no clusters to read.
- The content is LZNT1-compressed on disk, so `grep`/`strings` over the raw image find
  nothing — no `flag{`, and not the word `override` either.

The compressed stream still sits intact in unallocated space. The solver has to spot that the
record is compressed, find the LZNT1 data, and decompress it.

## Solution Steps

1. Unpack: `xz -dk blackbox.img.xz`.
2. Find deleted files: `fls -f ntfs -r -p -d blackbox.img` →
   `-/r * 82-128-2: LOGS/abort_log.txt`.
3. Try the obvious path: `icat -f ntfs blackbox.img 82` returns nothing, and `ntfsundelete`
   recovers nothing.
4. Inspect the record: `istat -f ntfs blackbox.img 82`.
   - `$STANDARD_INFORMATION` / `$FILE_NAME` flags: **`Archive, Compressed`**.
   - `$DATA (128-2) Non-Resident, Compressed  size: 19050` — with **no cluster list**.
     The file's metadata survived, but the pointer to its data did not.
   - Corroboration inside the image: `CONFIG/probe.cfg` contains `log_storage = compressed`.
5. A raw `grep -a 'flag{'` of the image returns 0 hits, which confirms the data isn't stored
   as plaintext.
6. Locate the data. NTFS compressed data starts each compression unit on a cluster
   boundary with a 2-byte LZNT1 chunk header whose signature bits are `0x3000` (a compressed
   chunk reads as `0xBxxx`, little-endian `xx Bx`). Either:
   - scan cluster boundaries (4096-byte clusters) for a valid chunk header, or
   - `strings -n 6` shows fragments of the log header split by LZNT1 tag bytes
     (`=== FLIG`, `HT COMPU`, `TER ABOR`). Take the offset and round it down to the cluster.

   The stream starts at **cluster 16896** (byte offset `69206016`), with first bytes
   `28 b4 00 3d 3d 3d 20 46 4c 49 47 …`.
7. Decompress LZNT1 chunks consecutively from that offset until a zero header. The output is
   the full 19,050-byte flight log, and line
   `T+00:41:17  override code: flag{...}` holds the flag.

   `solution/solve.py` does steps 6–7 with no dependencies:

   ```
   python3 solution/solve.py blackbox.img
   ```

   Off-the-shelf alternatives: `dissect.util.compression.lznt1`, or `RtlDecompressBuffer`
   (`COMPRESSION_FORMAT_LZNT1`) on Windows via ctypes.

### Why a raw grep can't shortcut it

LZNT1 only back-references within the current 4 KB chunk. Every word of the flag is spoken
earlier in the same chunk (`recorder=the_black_box  mode=kept_alive`,
`self-destruct override accepted`, `override code:`), so the compressor encodes the flag
mostly as back-references. The longest run of flag bytes stored literally is 8 characters.
Stripping the tag bytes (NULs) from the raw image does not reconstruct it either. The build
script asserts both.

## Verification

- Built on Linux Mint 22.3 (ntfs-3g 2022.10.3, sleuthkit). The build checks: pre-damage
  `icat` recovers the flag; `$DATA` is non-resident; no plaintext flag with or without NULs;
  post-damage `icat` recovers nothing; 0 `flag{` hits in the raw image.
- `solve.py` recovers the exact flag from `dist/blackbox.img.xz` after unpacking, on both
  Linux (Python 3.12) and Windows (Python 3.13).
- `blackbox.img` sha256 `4f4b4a1d59ecee4dbc2346b626825c41ba52448a9c15d8ac500d060ddfe23d65`.

## Hints (not in `challenge.yml`)

Not configured in CTFd. GMs can give these out if teams stall:

1. *"Look closely at the flags on the deleted file's record. The recorder didn't store its
   logs the way it stores everything else."* Points at `Compressed` in `istat` and at
   `log_storage = compressed` in `probe.cfg`.
2. If a team has found the compression but not the data: *"Compressed data starts on a
   cluster boundary, and it has a signature."* Points at the LZNT1 chunk header.

## Rebuilding

The build sources (`build_blackbox.sh`, `gen_log.py`, `mft_damage.py`) are kept by the author
outside the repo. Ask Jebediah Kerman for them. On Linux with `ntfs-3g`, `sleuthkit`, `attr`:

```
sudo FLAG='flag{...}' ./build_blackbox.sh
xz -9 -k blackbox.img
```

- `gen_log.py` writes the log and asserts the flag and its supporting lines share one LZNT1
  chunk. If you change the flag, keep its words present earlier in that chunk.
- Step 2b (`ntfswipe -u`) is essential: ntfs-3g writes a compressed file uncompressed first
  and frees the tail clusters without clearing them, which leaves a plaintext copy of the
  whole log in free space.
- `mft_damage.py` zeroes the `$DATA` mapping pairs and preserves the per-sector
  update-sequence fixup bytes, so the record still passes validation in `istat`.
