import sympy as sp
import math

p = 257
x = sp.symbols('x')

def basisPN(symbols, j):
    terms = []
    for k in range(len(symbols)):
        if j == k:
            continue

        inverse = pow(symbols[j] - symbols[k], -1, p)
        term = sp.Poly((x - symbols[k]) * inverse, x, modulus=p)
        terms.append(term)
    return math.prod(terms)

codewords = open('../dist/flight_plan.dat', 'rb').readlines()

plainwords = []
for codeword in codewords:
    codeword = codeword.strip()
    if len(codeword) != 36:
        raise ValueError('Expected twelve three-character symbols')

    symbols = [codeword[i : i + 3] for i in range(0, len(codeword), 3)]
    positions = []
    terms = []
    for i, symbol in enumerate(symbols):
        if symbol == b'???':
            continue
        if any(char not in b'0123456789abcdefABCDEF' for char in symbol):
            raise ValueError('Invalid hexadecimal symbol')
        value = int(symbol, 16)
        if value >= p:
            raise ValueError('Symbol outside the field')
        positions.append(i + 1)
        terms.append(value)

    if len(terms) < 8:
        raise ValueError('Not enough surviving symbols')

    # Interpolate using eight evaluations, preserving their original positions.
    polynomial = sp.Poly(0, x, modulus=p)
    for j in range(8):
        polynomial += terms[j] * basisPN(positions[:8], j)

    # SymPy uses signed field representatives; convert back to byte values.
    coefficients = [int(polynomial.nth(i)) % p for i in range(8)]
    for position, term in zip(positions, terms):
        result = 0
        for i, coeff in enumerate(coefficients):
            result += (coeff * (position ** i)) % p
        if result % p != term:
            raise ValueError('Surviving symbols are inconsistent')
    plainwords.append(bytes(coefficients))

flightPlan = b''.join(plainwords).rstrip(b'\x00').decode('ascii')
if 'flag{' not in flightPlan or '}' not in flightPlan.split('flag{', 1)[1]:
    raise ValueError('No flag recovered')
print(flightPlan)
