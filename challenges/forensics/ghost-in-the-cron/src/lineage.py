#!/usr/bin/env python3
"""Shared lineage logic for Ghost in the Cron (DFIR cluster #4).

One place defines how a `navd` generation's embedded key fragment is recovered
and how the four fragments combine into the mission-cache key. Both the cache
builder (src/make_cache.py) and the reference solver (solution/solve.py) import
this so the encrypt side and the solve side can never drift.

Obfuscation ladder (the implant "getting smarter" each self-revision):
  gen 1  plaintext                _KF = "...."
  gen 2  decimal char codes       _KF = bytes([..]).decode()
  gen 3  hex-encoded ascii        _KF = bytes.fromhex("..").decode()
  gen 4  base64                   _KF = base64.b64decode("..").decode()
"""
import base64
import hashlib
import re

GEN_RE = re.compile(r"^GEN\s*=\s*(\d+)", re.M)


def parse_gen(src):
    """Return the integer GEN marker declared in a generation's source."""
    m = GEN_RE.search(src)
    if not m:
        raise ValueError("no GEN marker in source")
    return int(m.group(1))


def extract_fragment(src):
    """Recover the plaintext key fragment from one generation's source text.

    Takes the FIRST `_KF = ...` assignment (each generation has exactly one) and
    reverses whichever obfuscation form that specific line uses. Anchoring on the
    nearest assignment matters when carving a raw image, where a generation's
    blocks can sit next to another generation's bytes -- matching by form-priority
    across a wide window would grab a neighbour's fragment."""
    m = re.search(r'_KF\s*=\s*(.+)', src)
    if not m:
        raise ValueError("no _KF assignment in source")
    rhs = m.group(1)

    # gen 4 -- base64
    b = re.search(r'base64\.b64decode\(\s*"([A-Za-z0-9+/=]+)"\s*\)', rhs)
    if b:
        return base64.b64decode(b.group(1)).decode()
    # gen 3 -- hex-encoded ascii
    h = re.search(r'bytes\.fromhex\(\s*"([0-9a-fA-F]+)"\s*\)', rhs)
    if h:
        return bytes.fromhex(h.group(1)).decode()
    # gen 2 -- decimal char codes
    d = re.search(r'bytes\(\s*\[([0-9,\s]+)\]\s*\)', rhs)
    if d:
        codes = [int(x) for x in d.group(1).split(",") if x.strip()]
        return bytes(codes).decode()
    # gen 1 -- plaintext literal
    p = re.search(r'"([^"]+)"', rhs)
    if p:
        return p.group(1)
    raise ValueError("unrecognized _KF form: %r" % rhs)


def lineage_key(fragments_in_gen_order):
    """key = SHA-256(kf1 || kf2 || kf3 || kf4), fragments in generation order."""
    if len(fragments_in_gen_order) != 4:
        raise ValueError("expected exactly 4 fragments, got %d" % len(fragments_in_gen_order))
    return hashlib.sha256("".join(fragments_in_gen_order).encode()).digest()


def fragments_from_sources(sources):
    """Given an unordered list of generation source texts, return the fragments
    ordered by their GEN marker (1..N)."""
    pairs = [(parse_gen(s), extract_fragment(s)) for s in sources]
    pairs.sort(key=lambda p: p[0])
    gens = [g for g, _ in pairs]
    if gens != list(range(1, len(gens) + 1)):
        raise ValueError("non-contiguous / duplicate generations: %r" % gens)
    return [f for _, f in pairs]
