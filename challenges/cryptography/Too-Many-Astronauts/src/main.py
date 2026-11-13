import math
import pickle
import yaml
from Crypto.Util.number import getPrime

debug = False
publishedFactors = set() # Store previously published factors to make all moduli coprime

if not debug:
    try:
        with open("publishedFactors.pkl", "rb") as f:
            publishedFactors = pickle.load(f)
    except FileNotFoundError:
        pass

with open('../challenge.yml', 'r') as f:
    metadata = yaml.safe_load(f)
flag = metadata['flags'][0]
if not isinstance(flag, str) or not flag.startswith('flag{') or not flag.endswith('}'):
    raise ValueError('challenge.yml must contain a static flag string')

plain = int.from_bytes(open("plain.txt", "r").read().replace('{{FLAG}}', flag).encode(), byteorder='big')
print(int.to_bytes(plain, (plain.bit_length() + 7) // 8).decode())  # Check that the plaintext is correct

e = 9
bitLength = 1400

for _ in range(e):
    p = getPrime(bitLength)
    q = getPrime(bitLength)
    n = p * q
    phi = (p - 1) * (q - 1)

    while p in publishedFactors or q in publishedFactors or math.gcd(e, phi) != 1:
        p = getPrime(bitLength)
        q = getPrime(bitLength)
        n = p * q
        phi = (p - 1) * (q - 1)

    d = pow(e, -1, phi)

    cipher = pow(plain, e, n)
    print(plain ** e > n)  # Check that m**e > n

    with open(f"encrypted{_}.txt", "w") as f:
        f.write(f'C = {hex(cipher)}\ne = {e}\nn = {hex(n)}')
        publishedFactors.add(p)
        publishedFactors.add(q)

if not debug:
    with open("publishedFactors.pkl", "wb") as f:
        pickle.dump(publishedFactors, f)