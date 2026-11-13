"""
Seal a flag for one of the games: prints the hex to paste into its FLAG_SEALED.

    python seal_flag.py 'flag{...}'               # rubik2d.py (the cube)
    python seal_flag.py --tesseract 'flag{...}'   # tesseract3d.py

The flag is XOR-ed with a keystream derived from the solved puzzle's state
(rubik2d.state_key / tesseract2d.state_key), so a game only stores bytes that
look random and can only decode them from a solved puzzle. This script is a
build-time tool: it is not part of the game binaries and holds no flag itself.
"""

import sys

from rubik2d import xor_stream

if __name__ == "__main__":
    args = sys.argv[1:]
    tesseract = "--tesseract" in args
    args = [a for a in args if a != "--tesseract"]
    if len(args) != 1:
        sys.exit(__doc__)
    if tesseract:
        from tesseract2d import Tesseract, state_key
        key = state_key(Tesseract())
    else:
        from rubik2d import Cube, state_key
        key = state_key(Cube())
    print(xor_stream(key, args[0].encode()).hex())
