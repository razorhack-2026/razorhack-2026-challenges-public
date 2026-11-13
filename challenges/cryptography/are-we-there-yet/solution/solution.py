import math

shares = []
with open('../src/shares.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        parts = line.split(', ')
        if len(parts) != 2:
            raise ValueError(f'Invalid share format: {line!r}')
        x_str, y_hex = parts
        shares.append((int(x_str), y_hex))

p = int('a105db01c4ca6f21c129479c720f425a4b20ec314b326ee6080079cbadcb4b71', 16)

def basis(x, i):
    terms = []
    for j in range(len(shares)):
        if i == j:
            continue

        terms.append((x - shares[j][0]) * pow(shares[i][0] - shares[j][0], -1, p))
    return math.prod(terms)

f_0 = 0
for i in range(len(shares)):
    y_i = int(shares[i][1][2:], 16)
    f_0 += y_i * basis(0, i) % p

f_0 %= p
print(f_0.to_bytes((f_0.bit_length() + 7) // 8, byteorder='big'))