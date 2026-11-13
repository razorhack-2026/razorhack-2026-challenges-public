# Reference solve. Connects to the relay and recovers the session token.
import argparse
import socket
import sys
import time

import sympy as sp
from fpylll import IntegerMatrix, LLL


BOUND_DELTA = 0.27
LATTICE_M = 5
LATTICE_T = 2
MAX_PAIRS = 12
TOKEN_BYTES = 16


def canonical(expression, u, x, y):
    poly = sp.Poly(expression, u, x, y)
    result = 0

    for (a, b, c), coefficient in poly.terms():
        reduced = min(b, c)
        result += coefficient * sp.expand(
            (u - 1) ** reduced * u ** a * x ** (b - reduced) * y ** (c - reduced)
        )

    return sp.expand(result)


def buildPolynomials(n, e, delta, m, t):
    x, y, u = sp.symbols('x y u')
    A = n + 1
    fu = A * x + u
    X = int(e ** delta)
    Y = 2 * int(n ** 0.5) + 1
    U = X * Y

    shifts = []

    for k in range(m + 1):
        for i in range(m - k + 1):
            shifts.append(canonical(x ** i * fu ** k * e ** (m - k), u, x, y))

    for j in range(1, t + 1):
        for k in range((m // t) * j, m + 1):
            shifts.append(canonical(y ** j * fu ** k * e ** (m - k), u, x, y))

    monomials = set()

    for shift in shifts:
        monomials.update(sp.Poly(shift, u, x, y).monoms())

    monomials = sorted(monomials, key=lambda mono: (sum(mono), mono))
    matrix = []

    for shift in shifts:
        poly = sp.Poly(shift, u, x, y)
        row = []

        for a, b, c in monomials:
            coefficient = poly.coeff_monomial((a, b, c))
            row.append(int(coefficient) * (U ** a) * (X ** b) * (Y ** c))

        matrix.append(row)

    basis = IntegerMatrix.from_matrix(matrix)
    LLL.reduction(basis)

    polynomials = []

    for i in range(len(shifts)):
        expression = 0

        for j, (a, b, c) in enumerate(monomials):
            entry = basis[i, j]

            if entry:
                value = (U ** a) * (X ** b) * (Y ** c)
                expression += (
                    sp.Rational(entry, value) * (u ** a) * (x ** b) * (y ** c)
                )

        polynomials.append(sp.expand(sp.expand(expression).subs(u, 1 + x * y)))

    return polynomials


def recoverPrivateExponent(n, e):
    x, y = sp.symbols('x y')
    start = time.time()
    polynomials = buildPolynomials(n, e, BOUND_DELTA, LATTICE_M, LATTICE_T)
    rows = len(polynomials)
    print(
        f'lattice {rows}x{rows} built in {time.time() - start:.1f}s',
        file=sys.stderr,
        flush=True,
    )

    pairs = []

    for i in range(min(rows - 1, 8)):
        for j in range(i + 1, min(rows, i + 6)):
            pairs.append((i, j))

    for i, j in pairs[:MAX_PAIRS]:
        start = time.time()
        resultant = sp.resultant(polynomials[i], polynomials[j], x)

        if resultant == 0:
            continue

        roots = sp.Poly(resultant, y).ground_roots()
        print(
            f'pair {i},{j}: {len(roots)} candidate(s) in {time.time() - start:.1f}s',
            file=sys.stderr,
            flush=True,
        )

        for yroot in roots:
            if not yroot.is_integer:
                continue

            y0 = int(yroot)
            phi = n + 1 + y0

            if phi <= 1:
                continue

            try:
                d = pow(e, -1, phi)
            except ValueError:
                continue

            if d > 0 and pow(2, e * d, n) == 2:
                return d

    return None


def sendLine(connection, text):
    connection.sendall(text.encode('ascii') + b'\n')


def readLine(reader):
    line = reader.readline()

    if not line:
        return None

    return line.decode('ascii', 'replace').strip()


def requestSession(connection, reader):
    sendLine(connection, 'KEY')
    fields = {}

    while True:
        line = readLine(reader)

        if line is None:
            raise RuntimeError('relay closed the connection')

        if line.startswith('SESSION '):
            fields['session'] = line.split()[1]
        elif line.startswith('N '):
            fields['n'] = int(line.split()[1], 16)
        elif line.startswith('E '):
            fields['e'] = int(line.split()[1], 16)
        elif line.startswith('C '):
            fields['c'] = int(line.split()[1], 16)
        elif line.startswith(('RATE LIMITED', 'TOO MANY', 'ERROR')):
            raise RuntimeError(line)

        if {'session', 'n', 'e', 'c'} <= fields.keys():
            return fields


def submitToken(connection, reader, session, token):
    sendLine(connection, f'AUTH {session} {token}')

    while True:
        line = readLine(reader)

        if line is None:
            raise RuntimeError('relay closed the connection')

        if line.startswith(('ACCEPTED', 'REJECTED')):
            return line


def main():
    argumentParser = argparse.ArgumentParser(
        description='Solve a Swarm Key Shuffle relay session.',
    )
    argumentParser.add_argument('--host', default='127.0.0.1')
    argumentParser.add_argument('--port', type=int, default=31337)
    arguments = argumentParser.parse_args()

    with socket.create_connection((arguments.host, arguments.port), timeout=30) as connection:
        reader = connection.makefile('rb')
        session = requestSession(connection, reader)
        print(f'session {session["session"]}', file=sys.stderr, flush=True)

        d = recoverPrivateExponent(session['n'], session['e'])

        if d is None:
            raise SystemExit('Boneh-Durfee failed; request another session')

        token = pow(session['c'], d, session['n']).to_bytes(TOKEN_BYTES, 'big').hex()
        print(submitToken(connection, reader, session['session'], token))


if __name__ == '__main__':
    main()

