import math
from sympy import integer_nthroot
import os

ciphertexts = []
moduli = []

for file in os.listdir('pub_keys'):
    with open(f'pub_keys/{file}', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('C ='):
                ciphertexts.append(int(line.split('=')[1].strip(), 16))
            elif line.startswith('n ='):
                moduli.append(int(line.split('=')[1].strip(), 16))

e = 9

# Chinese Remainder Theorem
M = math.prod(moduli)
plaintext = 0
for c_i, m_i in zip(ciphertexts, moduli):
    M_i = M // m_i
    y_i = pow(M_i, -1, m_i)
    plaintext += c_i * M_i * y_i
plaintext = plaintext % M

plaintext, isValid = integer_nthroot(plaintext, e)
print(isValid)  # Check that the plaintext is a perfect eth power
print(bytes.fromhex(hex(plaintext)[2:]).decode())
