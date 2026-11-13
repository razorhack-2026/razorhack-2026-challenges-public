import math

def isPerfectSquare(x):
    if x < 0:
        return False
    t = math.isqrt(x)
    return t * t == x

with open('../dist/encrypted.txt', 'r') as f:
    lines = f.readlines()
    for line in lines:
        if line.startswith('e ='):
            e = int(line.split('=')[1].strip(), 16)
        elif line.startswith('n ='):
            n = int(line.split('=')[1].strip(), 16)
        elif line.startswith('c ='):
            c = int(line.split('=')[1].strip(), 16)

expansion = []
div = -1
rem = -1
eBuf = e
nBuf = n

while rem != 0:
    div, rem = divmod(eBuf, nBuf)

    expansion.append(div)
    eBuf, nBuf = (nBuf, rem)

prev2_numer, prev_numer = 0, 1
prev2_denom, prev_denom = 1, 0
for a in expansion:
    # Generate continued fraction convergent
    k = a * prev_numer + prev2_numer
    d = a * prev_denom + prev2_denom
    prev2_numer = prev_numer
    prev_numer = k
    prev2_denom = prev_denom
    prev_denom = d

    if k == 0:
        continue

    # Test if k/d == e/n
    # Divisibility test
    if (e * d - 1) % k != 0:
        continue

    phi = (e * d - 1) // k

    # Sum of primes candidate
    S = n - phi + 1

    # Discriminant check (x^2 - S*x + n = 0)
    delta = S ** 2 - 4 * n
    if delta < 0:
        continue
    elif not isPerfectSquare(delta):
        continue

    sqrtDelta = math.isqrt(delta)
    p = (S + sqrtDelta) // 2
    q = (S - sqrtDelta) // 2

    # Verify this solution
    testPhi = (p - 1) * (q - 1)
    if e * d % testPhi == 1:
        print(f'Found d = {hex(d)}')
        break

m = pow(c, d, n)
m_bytes = m.to_bytes((m.bit_length() + 7) // 8)
print(m_bytes.decode('utf-8'))