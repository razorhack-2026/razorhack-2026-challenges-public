from pathlib import Path
import argparse
import numpy as np
from PIL import Image


p = int('8c0cbcbc4f4769ccc6e6f767f426ff71febf667c07aa311582d768f2a5b9ea97', 16)
sharesNeeded = 31


parser = argparse.ArgumentParser(description='Recover the override key from share PNGs')
parser.add_argument('share_directory', nargs='?', type=Path,
                    default=Path(__file__).resolve().parents[1] / 'dist' / 'shares')
args = parser.parse_args()
share_directory = args.share_directory

shares = []
valueLength = (p.bit_length() + 7) // 8
recordLength = 48 + valueLength
paddedLength = ((recordLength + 47) // 48) * 48

# Recover the original RGB bytes from the enlarged pixel blocks.
for path in sorted(Path(share_directory).glob('share_*.png')):
    with Image.open(path) as image:
        img = np.array(image.convert('RGB'))
    if img.shape != (paddedLength // 48 * 32, 16 * 32, 3):
        raise ValueError(f'Unexpected image dimensions: {path.name}')
    pixels = img[::32, ::32]
    if not np.array_equal(img, pixels.repeat(32, axis=0).repeat(32, axis=1)):
        raise ValueError(f'Nonuniform encoded pixel block: {path.name}')
    share_bytes = pixels.tobytes()
    if (share_bytes[:6] != b'OVRDKY'
            or share_bytes[38:48] != bytes(10)
            or any(share_bytes[recordLength:])):
        raise ValueError(f'Invalid record header or padding: {path.name}')
    x_val = int.from_bytes(share_bytes[6:38], 'big')
    y_val = int.from_bytes(share_bytes[48:recordLength], 'big')
    if not 0 < x_val < p or not 0 <= y_val < p:
        raise ValueError(f'Record value outside the field: {path.name}')
    shares.append((x_val, y_val))

if len(shares) < sharesNeeded:
    raise ValueError(f'Found {len(shares)} shares in {share_directory}; '
                     f'need at least {sharesNeeded}')
if len({share[0] for share in shares}) != len(shares):
    raise ValueError('Duplicate share indices')

# Weighted parity checks cancel the unmodified polynomial evaluations.
weights = []
for i, (x_val, y_val) in enumerate(shares):
    denominator = 1
    for j, (otherX, otherY) in enumerate(shares):
        if i != j:
            denominator = denominator * (x_val - otherX) % p
    weights.append(pow(denominator, -1, p))

syndromes = []
for j in range(len(shares) - sharesNeeded):
    syndromes.append(sum(weight * y_val * pow(x_val, j, p)
                        for weight, (x_val, y_val)
                        in zip(weights, shares)) % p)

# Berlekamp-Massey: coefficients are stored in ascending power order.
C, B = [1], [1]
L, b, m = 0, 1, 1
for N in range(len(syndromes)):
    discrepancy = syndromes[N]
    for j in range(1, L + 1):
        discrepancy += C[j] * syndromes[N - j]
    discrepancy %= p
    if discrepancy == 0:
        m += 1
        continue
    previous = C[:]
    factor = discrepancy * pow(b, -1, p) % p
    C += [0] * max(0, len(B) + m - len(C))
    for j in range(len(B)):
        C[j + m] = (C[j + m] - factor * B[j]) % p
    if 2 * L <= N:
        L = N + 1 - L
        B, b, m = previous, discrepancy, 1
    else:
        m += 1

if 2 * L > len(syndromes):
    raise ValueError('Too many modified shares to recover uniquely')
goodShares, badShares = [], []
for x_val, y_val in shares:
    inverseX = pow(x_val, -1, p)
    locator = sum(coefficient * pow(inverseX, j, p)
                for j, coefficient in enumerate(C)) % p
    if locator == 0:
        badShares.append(x_val)
    else:
        goodShares.append((x_val, y_val))
if len(badShares) != L or len(goodShares) < sharesNeeded:
    raise ValueError('Error locator does not identify a valid set of shares')

# Interpolate from good shares, and verify the polynomial against all inputs.
selected = goodShares[:sharesNeeded]

# Evaluate the interpolated polynomial at zero and at every received index.
recoveredValues = []
for atX in [0] + [share[0] for share in shares]:
    value = 0
    for i, (x_val, y_val) in enumerate(selected):
        numerator, denominator = 1, 1
        for j, (otherX, otherY) in enumerate(selected):
            if i != j:
                numerator = numerator * (atX - otherX) % p
                denominator = denominator * (x_val - otherX) % p
        value += y_val * numerator * pow(denominator, -1, p)
    recoveredValues.append(value % p)

secret = recoveredValues[0]
mismatches = []
for (x_val, y_val), recovered in zip(shares, recoveredValues[1:]):
    if recovered != y_val:
        mismatches.append(x_val)
if mismatches != badShares:
    raise ValueError('Recovered polynomial does not match the error locations')

print(f'Modified share indices: {badShares}')
print(f'Recovered override key (hex): {secret:x}')
