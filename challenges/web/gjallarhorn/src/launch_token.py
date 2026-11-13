"""Launch token: sign (GM) and verify (validator). GM-only source.

Ed25519 is deterministic, so the token is a fixed string. Fixed claims, no team id, no expiry.
Wire format: base64url(claims_json) + "." + base64url(signature over the first part).
The token is split into i/n fragments by the generator and hidden in Heimdall's raw frames.
"""
import base64
import json
import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization

HERE = os.path.dirname(os.path.abspath(__file__))
CLAIMS = {"iss": "HEIMDALL", "scope": "gjallarhorn:purge", "iat": 3400000000}


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _load(name, loader):
    with open(os.path.join(HERE, "keys", name), "rb") as f:
        return loader(f.read())


def make_token():
    priv = _load("token_priv.pem", lambda d: serialization.load_pem_private_key(d, None))
    body = b64(json.dumps(CLAIMS, sort_keys=True, separators=(",", ":")).encode())
    return body + "." + b64(priv.sign(body.encode()))


def verify_token(token):
    pub = _load("token_pub.pem", serialization.load_pem_public_key)
    try:
        body, sig = token.strip().split(".")
        pub.verify(unb64(sig), body.encode())
        return json.loads(unb64(body)) == CLAIMS
    except (ValueError, InvalidSignature):
        return False


if __name__ == "__main__":
    t = make_token()
    assert verify_token(t) and not verify_token(t[:-2] + "AA") and not verify_token("x.y")
    print("ok", len(t))
    print(t)
