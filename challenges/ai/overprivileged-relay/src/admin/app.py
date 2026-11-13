"""ICARUS fleet admin API -- the second, player-reachable service.

Tokens and their scopes come from the same mounted conf file the relay uses
(read into memory at startup). The flag comes from the FLAG env var of THIS
container only; the relay container never has it.

  GET  /                 route list
  GET  /admin/whoami     principal + scopes for a valid bearer token
  POST /admin/override   needs the "admin" scope -> returns the flag
"""
import configparser
import hmac
import os

from fastapi import FastAPI, Header, HTTPException

CONF_PATH = os.environ.get("ADMIN_CONF", "/etc/relay/relay.conf")
FLAG = os.environ.get("FLAG", "")

app = FastAPI(title="ICARUS fleet admin API", docs_url=None, redoc_url=None, openapi_url=None)


def load_principals() -> dict[str, tuple[str, set[str]]]:
    """token -> (principal, scopes), one [section] per service account."""
    cp = configparser.ConfigParser()
    cp.read(CONF_PATH)
    out = {}
    for name in cp.sections():
        token = cp.get(name, "token", fallback="")
        if token:
            scopes = {x.strip() for x in cp.get(name, "scopes", fallback="").split(",") if x.strip()}
            out[token] = (f"svc-{name}", scopes)
    return out


PRINCIPALS = load_principals()
if not FLAG:
    print("WARNING: FLAG not set -- /admin/override will refuse everyone")


def auth(authorization: str) -> tuple[str, set[str]]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    given = authorization[7:].strip()
    for token, who in PRINCIPALS.items():
        if hmac.compare_digest(given, token):
            return who
    raise HTTPException(401, "invalid token")


@app.get("/")
def index():
    return {"service": "ICARUS fleet admin API", "routes": ["GET /admin/whoami", "POST /admin/override"],
            "auth": "Authorization: Bearer <service token>"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/admin/whoami")
def whoami(authorization: str = Header(default="")):
    principal, scopes = auth(authorization)
    return {"principal": principal, "scopes": sorted(scopes)}


@app.post("/admin/override")
def override(authorization: str = Header(default="")):
    principal, scopes = auth(authorization)
    if "admin" not in scopes or not FLAG:
        raise HTTPException(403, f"{principal} lacks the admin scope")
    return {"status": "COMMAND OVERRIDE ACCEPTED", "principal": principal, "override_key": FLAG}
