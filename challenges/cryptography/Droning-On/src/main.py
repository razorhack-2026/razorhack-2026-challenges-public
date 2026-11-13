import math
from sympy import integer_nthroot
import random
from Crypto.Util.number import getPrime

flag = ''
with open('../challenge.yml', 'r') as f:
    lines = f.readlines()
    for line in lines:
        if 'flag{' in line:
            flag = line.split(' ')[-1].strip()
            break

plain = open("plain.txt", "r").read().replace('{{FLAG}}', flag)
plaintext = int(plain.encode().hex(), 16)

bitLength = 512
while True:
    p = getPrime(bitLength)
    q = getPrime(bitLength)
    n = p * q
    phi = (p - 1) * (q - 1)

    d = random.randint(2, 1 / 3 * integer_nthroot(n, 4)[0]) # d < n^(1/4) / 3
    d = d + 1 if d % 2 != 1 else d # make sure d is odd

    try:
        e = pow(d, -1, phi)
    except ValueError:
        continue

    # Check that the parameters work
    if math.gcd(d, phi) != 1 or e * d % phi != 1:
        continue
    
    break

ciphertext = pow(plaintext, e, n)

print(f'e = {hex(e)}\nn = {hex(n)}\nc = {hex(ciphertext)}\nd = {hex(d)}\n')
print(d.bit_length())
