#!/usr/bin/env python3
"""
Field Diagnostic — build script (GM-only).

Emits the challenge program's SOURCE (src/diagnostic_rendered.py, for GM
reference) and the shipped BYTECODE (dist/diagnostic.pyc, Python 3.8).

No XOR anywhere (deliberately — XOR-keystream recovery is already well covered
by other challenges). Two non-XOR mechanisms, both plainly readable once the
.pyc is decompiled:

  * Service-code gate: each code byte is left-rotated by _ROT bits and compared
    to _TARGET, so CODE = rotr(_TARGET, _ROT) byte-wise.
  * Full readout: each readout byte is left-rotated by _ROT bits, then the
    bytes are permuted into positions given by a permutation seeded from the
    service code (random.Random(int.from_bytes(code,"big")).shuffle). The
    rotation hides the byte values (so the constant is garbage, not a readable
    anagram) and the permutation hides their order. Recovering the code
    reproduces the permutation and un-rotates -> the readout.

The service code and flag live ONLY here. Run with Python 3.8 so the emitted
.pyc is 3.8 bytecode:
    uv run --python 3.8 python src/build.py
"""
import os
import py_compile
import random

# ── secrets (never shipped) ──────────────────────────────────────────────
CODE = b"svc-7731-unlock"                       # the service code to recover
FLAG = b"flag{bytecode_still_reads_like_source}"
READOUT = b"FC-200 cal grid aligned / " + FLAG  # the gated "full readout" text
_ROT = 3


def _rotl(b, n):
    return ((b << n) | (b >> (8 - n))) & 0xFF


_TARGET = bytes(_rotl(c, _ROT) for c in CODE)

# rotate each readout byte, then permute positions with a code-seeded shuffle
_rotated = bytes(_rotl(READOUT[i], _ROT) for i in range(len(READOUT)))
_order = list(range(len(READOUT)))
random.Random(int.from_bytes(CODE, "big")).shuffle(_order)
_SCRAMBLED = bytes(_rotated[_order[i]] for i in range(len(READOUT)))


def _fmt(b: bytes) -> str:
    # real bytes literal -> lands in co_consts as a bytes object
    return 'b"' + "".join(f"\\x{x:02x}" for x in b) + '"'


SRC = '''\
#!/usr/bin/env python3
"""FC-200 Field Diagnostic utility (competitor-facing program)."""
import random

_ROT = {rot}
_TARGET = {target}
_SCRAMBLED = {scrambled}


def _rotl(b, n):
    return ((b << n) | (b >> (8 - n))) & 0xFF


def _rotr(b, n):
    return ((b >> n) | (b << (8 - n))) & 0xFF


def _roll(data):
    out = bytearray(len(data))
    for i in range(len(data)):
        out[i] = _rotl(data[i], _ROT)
    return bytes(out)


def _unlock(code):
    n = len(_SCRAMBLED)
    order = list(range(n))
    random.Random(int.from_bytes(code, "big")).shuffle(order)
    out = bytearray(n)
    for i in range(n):
        out[order[i]] = _rotr(_SCRAMBLED[i], _ROT)
    return bytes(out).decode()


def main():
    print("FC-200 Field Diagnostic  v3.1")
    print("panel: NOMINAL   bus: NOMINAL   cal: LOCKED")
    code = input("enter service code for full calibration readout: ").strip().encode()
    if len(code) == len(_TARGET) and _roll(code) == _TARGET:
        print("-- full calibration readout --")
        print(_unlock(code))
    else:
        print("service code rejected - readout stays locked")


if __name__ == "__main__":
    main()
'''.format(rot=_ROT, target=_fmt(_TARGET), scrambled=_fmt(_SCRAMBLED))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    rendered = os.path.join(here, "diagnostic_rendered.py")
    with open(rendered, "w") as f:
        f.write(SRC)
    out = os.path.join(root, "dist", "diagnostic.pyc")
    py_compile.compile(rendered, cfile=out, dfile="diagnostic.py",
                       optimize=0, invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
    print(f"wrote {out}")
    with open(out, "rb") as f:
        blob = f.read()
    assert b"flag{" not in blob, "FLAG substring leaked into dist/ bytecode"
    assert CODE not in blob, "service code leaked into dist/ bytecode"
    # the rotated+scrambled readout should not expose readable flag characters
    assert b"flag" not in _SCRAMBLED and b"}" not in _SCRAMBLED, "readout not hidden"
    print("ok: no flag{ substring / code plaintext; readout constant is hidden")


if __name__ == "__main__":
    main()
