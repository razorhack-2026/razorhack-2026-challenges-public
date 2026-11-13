"""Phase 0 unit test -- authorization-tag round-trip and key recovery.

Imports the SHIPPED module (dist/authtag.py), proving the artifact players get is
by itself enough to reconstruct the secret signing key from a handful of records:

  * compute_tag is deterministic and in range,
  * six records have six distinct x (the Vandermonde system is well-posed),
  * recover_coefficients returns the true (a, b, c) from 3 records,
  * the recovered key validates on the 3 held-out records,
  * the shipped module carries no coefficients in its own environment.

Run: python3 solution/test_authtag.py
"""
import os
import secrets
import sys

# the shipped module has no coefficients in its environment; make that true here too
for _k in ("AUTH_A", "AUTH_B", "AUTH_C"):
    os.environ.pop(_k, None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dist"))
import authtag as A  # noqa: E402


def main():
    P = A.P
    a = 1 + secrets.randbelow(P - 1)
    b = 1 + secrets.randbelow(P - 1)
    c = 1 + secrets.randbelow(P - 1)

    subjects = ["KT-1A2B", "KT-3C4D", "KT-5E6F", "KT-7G8H", "KT-9J0K", "KT-2L3M"]
    resources = ["reactor-telemetry", "medbay-records", "nav-charts",
                 "cargo-manifest", "comms-log", "command-archive"]
    recs = []  # (msg, T)
    for i in range(6):
        nonce = secrets.token_hex(8)
        msg = A.canonical_message(40001 + i, subjects[i], resources[i], "approved", nonce)
        recs.append((msg, A.compute_tag(msg, a, b, c)))

    checks = []
    checks.append(("tag deterministic", A.compute_tag(recs[0][0], a, b, c) == recs[0][1]))
    checks.append(("tags in range [0, p)", all(0 <= T < P for _, T in recs)))
    xs = [A.message_point(m) for m, _ in recs]
    checks.append(("6 records -> 6 distinct x", len(set(xs)) == 6))

    pts3 = [(A.message_point(m), T) for m, T in recs[:3]]
    ra, rb, rc = A.recover_coefficients(pts3)
    checks.append(("recovers (a, b, c) from 3 records", (ra, rb, rc) == (a, b, c)))
    checks.append(("recovered key validates on held-out 3",
                   all(A.compute_tag(m, ra, rb, rc) == T for m, T in recs[3:])))
    checks.append(("no coefficients in shipped env", A.coefficients_from_env() is None))

    passed = 0
    for label, cond in checks:
        print(("PASS " if cond else "FAIL ") + label)
        passed += bool(cond)
    print(f"{passed}/{len(checks)} passed")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
