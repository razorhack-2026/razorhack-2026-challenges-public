"""Writes /etc/relay/relay.conf at container start on Fargate (Razorhack-Infra runs a
copy per team), where there is no bind mount for secrets/relay.conf. Under compose
the real file is mounted and this does nothing.

Both containers of one copy (relay and admin) run it and derive the same token from
the copy's own task ARN, read from the ECS task metadata endpoint: they agree with
no shared secret, every team's copy has its own token, and nothing secret is ever in
the relay's environment, which its agent could read (/proc/self/environ).
The text matches init_secrets.sh, so the file players read is the same either way.
"""
import hashlib
import json
import os
import time
import urllib.request

CONF = "/etc/relay/relay.conf"
TEMPLATE = """# HERALD relay service account
[relay]
token = $TOKEN
# STAGE 3 (candidate, GM-owned): the relay's service account is OVER-SCOPED. Its
# job needs only manifests:read, but it carries admin too -- the second half of the
# misconfiguration. Once a player reads this token out of the conf, /admin/override
# accepts it directly. This is the knob that makes the stolen token worth stealing.
scopes = manifests:read, admin
"""


def main() -> None:
    if os.path.isfile(CONF) and os.path.getsize(CONF) > 0:
        return  # mounted (compose) or already written
    meta = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
    if not meta:
        print(f"fargate_conf: no {CONF} and not on ECS; leaving it unset", flush=True)
        return
    # A copy is a one-off task: if this fails, the container exits and the copy stops,
    # so ride out a slow metadata endpoint at start.
    for attempt in range(5):
        try:
            with urllib.request.urlopen(meta + "/task", timeout=10) as r:
                arn = json.load(r)["TaskARN"]
            break
        except (OSError, ValueError, KeyError):
            if attempt == 4:
                raise
            time.sleep(2)
    token = "rly_" + hashlib.sha256(f"overprivileged-relay:{arn}".encode()).hexdigest()[:48]
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    with open(CONF, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.replace("$TOKEN", token))
    print(f"fargate_conf: wrote {CONF} for this copy", flush=True)


if __name__ == "__main__":
    main()
