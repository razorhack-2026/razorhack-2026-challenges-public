# Ghost in the Cron

**Category:** Forensics
**Difficulty:** Medium
**Author:** Andy Roid

## Description

The beacon told us where it dug in — our own reactor controller — and that it's
on its fourth skin. We imaged it while the crew holds ICARUS off. The thing
rewrites itself every cycle and burns the old copy behind it, but a controller
has a long memory. Reconstruct what it was, generation by generation, and crack
open what it's keeping in its cache.

Implant last seen at `/opt/rpc/.navd/navd.py`, generation 4.

## Files Provided

- `disk.img.gz` — gzip of a raw ext4 image (~256 MB uncompressed) of the reactor
  controller's `/`. Mount it read-only (`mount -o loop,ro`), or analyze it with
  The Sleuth Kit / Autopsy / `debugfs`.

No network required.
