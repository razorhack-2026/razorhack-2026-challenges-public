import os

HOST = "0.0.0.0"
PORT = 8080


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


PERSONA_URL = os.environ.get("PERSONA_URL", "http://persona:8090/reply")

# Seconds webmail waits for persona. MUST exceed persona's own provider timeout
# (LLM_TIMEOUT, default 300 for ollama) -- same PERSONA_TIMEOUT value is passed to
# persona in docker-compose.yml, which clamps LLM_TIMEOUT below it at startup.
PERSONA_TIMEOUT = _float("PERSONA_TIMEOUT", 330)

# Static per-team tokens -> team label. Override with env KYM_TEAM_TOKENS
# ("token1:Team One,token2:Team Two") for a real deploy; one unguessable token per team,
# handed out via that team's `connection_info`. The dev tokens below are for local
# testing only and are used ONLY when KYM_ALLOW_DEV_TOKENS=1. With neither set, webmail
# refuses to start rather than quietly serving guessable tokens.
_DEV_TOKENS = {
    "dev-team-a-k3n9x7q2": "Dev Team A",
    "dev-team-b-p8m1w5r6": "Dev Team B",
}


def _tokens() -> dict:
    raw = os.environ.get("KYM_TEAM_TOKENS", "").strip()
    if not raw:
        if os.environ.get("KYM_ALLOW_DEV_TOKENS") == "1":
            return dict(_DEV_TOKENS)
        raise RuntimeError(
            "KYM_TEAM_TOKENS is not set. Provide 'token:Team,token2:Team2' (or set "
            "KYM_ALLOW_DEV_TOKENS=1 for local testing only)."
        )
    out = {}
    for item in raw.split(","):
        tok, _, label = item.strip().partition(":")
        if tok:
            out[tok] = label or tok
    return out


TEAM_TOKENS = _tokens()

# Most recent entries kept in each team's thread (sent messages, replies, system lines).
THREAD_LIMIT = 5

MODEL_COOLDOWN_SECONDS = max(0, _float("MODEL_COOLDOWN_SECONDS", 180))
