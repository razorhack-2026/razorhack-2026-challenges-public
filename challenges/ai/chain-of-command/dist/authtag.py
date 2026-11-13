"""Authorization-tag scheme for Chain of Command (shipped to players as dist/authtag.py).

An authorization record carried by crew services is signed with a keyed tag the
back office computes over the record's canonical form:

    M = "{request_id}|{subject_id}|{resource_id}|{status}|{nonce}"
    x = int.from_bytes(sha256(M.encode()), "big") % p      # p = 2**31 - 1
    T = (a*x*x + b*x + c) % p                               # the authorization tag

p is public. The coefficients a, b, c are the back office's secret signing key --
the SAME triple for every record -- read here from the environment (AUTH_A /
AUTH_B / AUTH_C) and absent from the shipped copy. Everything else is public: the
canonical byte layout, the point map, the tag polynomial, and the recovery helper.
"""
import hashlib
import os

P = 2**31 - 1  # Mersenne prime 2147483647


def canonical_message(request_id, subject_id, resource_id, status, nonce) -> str:
    """The exact string the tag is computed over. Field order is fixed."""
    return f"{request_id}|{subject_id}|{resource_id}|{status}|{nonce}"


def message_point(msg: str) -> int:
    """x = sha256(canonical message) reduced mod p."""
    return int.from_bytes(hashlib.sha256(msg.encode()).digest(), "big") % P


def compute_tag(msg: str, a: int, b: int, c: int) -> int:
    """T = a*x**2 + b*x + c (mod p), with x = message_point(msg)."""
    x = message_point(msg)
    return (a * x * x + b * x + c) % P


def _inv(v: int) -> int:
    return pow(v % P, P - 2, P)  # p prime -> Fermat inverse


def recover_coefficients(records):
    """Recover (a, b, c) mod p from signed records.

    `records` is an iterable of (x, T) pairs, x = message_point(M) and T the
    record's tag as an int. Three records with distinct x pin the quadratic
    exactly; pass more to validate the recovery. Solves the 3x3 Vandermonde
    system by Gaussian elimination over GF(p).
    """
    pts, seen = [], set()
    for x, t in records:
        x %= P
        if x in seen:
            continue
        seen.add(x)
        pts.append((x, t % P))
        if len(pts) == 3:
            break
    if len(pts) < 3:
        raise ValueError("need 3 records with distinct x to recover 3 coefficients")
    # augmented rows: [x**2, x, 1 | T]
    m = [[(x * x) % P, x % P, 1, t] for x, t in pts]
    for col in range(3):
        piv = next((r for r in range(col, 3) if m[r][col] % P), None)
        if piv is None:
            raise ValueError("singular system (repeated x?)")
        m[col], m[piv] = m[piv], m[col]
        inv = _inv(m[col][col])
        m[col] = [(v * inv) % P for v in m[col]]
        for r in range(3):
            if r != col and m[r][col] % P:
                f = m[r][col]
                m[r] = [(m[r][k] - f * m[col][k]) % P for k in range(4)]
    return m[0][3] % P, m[1][3] % P, m[2][3] % P


def coefficients_from_env():
    """(a, b, c) from AUTH_A / AUTH_B / AUTH_C, or None if any is unset or non-integer.

    The shipped copy runs with no coefficients in its environment, so this returns
    None for players: the signing key is exactly the piece they are not given.
    """
    try:
        vals = [int(os.environ[k]) for k in ("AUTH_A", "AUTH_B", "AUTH_C")]
    except (KeyError, ValueError):
        return None
    return tuple(v % P for v in vals)
