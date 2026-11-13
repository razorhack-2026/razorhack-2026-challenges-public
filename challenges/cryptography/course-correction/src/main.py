import Crypto.Util.number
import sympy as sp
import random
import yaml
import numpy as np
from pathlib import Path
from PIL import Image

x = sp.symbols('x')

with (Path(__file__).resolve().parent.parent / 'challenge.yml').open() as f:
    flag = yaml.safe_load(f)['flags'][0]
    overrideKey = flag[5:-1] # Remove the "flag{" and "}" from the flag to get the override key

sharesNeeded, totalShares = 31, 63
maxModified = 16
# p = int(Crypto.Util.number.getPrime(256))
p = int('8c0cbcbc4f4769ccc6e6f767f426ff71febf667c07aa311582d768f2a5b9ea97', 16)
print(f"p: {hex(p)}")
secret = int(overrideKey, 16)
while True:
    if secret < p:
        break
    p = Crypto.Util.number.getPrime(256)
    secret = int(overrideKey, 16)

# Keep the private polynomial coefficients beside the generator, never in dist/.
coefficients_path = Path(__file__).parent / "coefficients.yml"
if coefficients_path.exists():
    with coefficients_path.open() as coefficient_file:
        coefficient_data = yaml.safe_load(coefficient_file)
    if (not isinstance(coefficient_data, dict)
            or coefficient_data.get("modulus") != p
            or coefficient_data.get("threshold") != sharesNeeded):
        raise ValueError("Saved coefficients do not match the modulus and threshold")
    coefficients = coefficient_data.get("coefficients")
    if (not isinstance(coefficients, list)
            or len(coefficients) != sharesNeeded - 1
            or any(type(value) is not int or not 0 <= value < p
                    for value in coefficients)
            or coefficients[-1] == 0):
        raise ValueError("Saved coefficients are invalid")
else:
    coefficients = [random.randint(0, p-1) for _ in range(sharesNeeded - 1)]
    coefficients[-1] = random.randint(1, p-1)
    with coefficients_path.open("x") as coefficient_file:
        yaml.safe_dump({
            "modulus": p,
            "threshold": sharesNeeded,
            "coefficients": coefficients,
        }, coefficient_file)

f = sum((coefficient * x**i for i, coefficient in enumerate(coefficients, start=1)), secret) % p
shares = []
for i in range(1, totalShares + 1):
    shares.append((i, f.subs(x, i)))

# Verify that the shares can reconstruct the secret
reconstructed_secret = 0
for i in range(totalShares):
    x_val = shares[i][0]
    y_val = shares[i][1]
    numerator = 1
    denominator = 1
    for j in range(totalShares):
        if i != j:
            numerator *= (0 - shares[j][0])
            denominator *= (shares[i][0] - shares[j][0])
    reconstructed_secret += y_val * numerator * pow(denominator, -1, p)
reconstructed_secret %= p

print(f"Original secret: {secret}")
print(f"Reconstructed secret: {reconstructed_secret}")

assert totalShares >= sharesNeeded + 2 * maxModified
random.seed(42)
for index in random.sample(range(totalShares), maxModified):
    oldY = shares[index][1]
    newY = random.randint(0, p-1)
    while newY == oldY:
        newY = random.randint(0, p-1)
    shares[index] = (shares[index][0], newY)

for share in shares:
    header = b'OVRDKY' + share[0].to_bytes(32, "big") + b'\0\0\0\0\0\0\0\0\0\0'
    imgWidth = len(header) // 3

    share_bytes = header + int(share[1]).to_bytes((p.bit_length() + 7) // 8, "big")
    print(f"Share {share[0]} bytes length: {len(share_bytes)}")
    if len(share_bytes) % (imgWidth * 3) != 0:
        share_bytes += b'\0' * (imgWidth * 3 - len(share_bytes) % (imgWidth * 3))

    imgHeight = len(share_bytes) // (imgWidth * 3)
    img = np.zeros((imgHeight, imgWidth, 3), dtype=np.uint8)
    pixels = [(i, share_bytes[i], share_bytes[i + 1], share_bytes[i + 2]) for i in range(0, len(share_bytes), 3)]
    for i, r, g, b in pixels:
        img[i // (imgWidth * 3), (i // 3) % imgWidth] = [r, g, b]

    scale = 32
    preview = Image.fromarray(img)
    preview = preview.resize(
        (imgWidth * scale, imgHeight * scale),
        resample=Image.Resampling.NEAREST,
    )
    preview_path = Path(__file__).parent.parent / f"dist/shares/share_{share[0]}.png"
    preview.save(preview_path, format="PNG")
    print(f"Saved share image to {preview_path}")
