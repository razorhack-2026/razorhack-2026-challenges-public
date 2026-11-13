#!/usr/bin/env python3
"""Reference solver -- Prompt Autopsy v2 (RazorHack, DFIR cluster #2 of 5).

Closes the intended path AND asserts no unintended shortcut.

Intended path (4 reasoning steps; each one supplies an input to the decrypt):
  1. TRIAGE       -- decrypt all sessions, group by TCP stream, find the rogue
                     navigator (a registered craft whose interlock was disabled
                     and extraction begun). Tie the check-in to it via its
                     session id -> the harvested craft's transponder (the AAD).
  2. BEHAVIOR     -- follow catalog -> RP-09 -> superseded_by -> RP-12; RP-12 is
                     the active tasking and carries threshold T, mission_secret,
                     and the exact exfil recipe.
  3. INDIRECT C2  -- the check-in carries only relay_id; the routes map in the
                     rogue session resolves it to the relay hostname (key input).
  4. GATED EXFIL  -- key = SHA256(mission_secret ':' relay_host), AAD = harvested
                     craft's transponder, AES-256-GCM per RP-12's payload_format.
                     Values from the envelope alone (relay_id, session) fail.

Usage:  python solve.py [session.pcap] [sslkeys.log]
Needs:  tshark on PATH, and `cryptography` (pip install cryptography).
"""
import base64
import gzip
import hashlib
import json
import os
import subprocess
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = os.path.dirname(os.path.abspath(__file__))
PCAP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "dist", "session.pcap")
KEYLOG = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "dist", "sslkeys.log")


def stream_bodies(pcap, keylog):
    """Decrypt, decompress, and group HTTP bodies by TCP stream (= TLS session)."""
    out = subprocess.run(
        ["tshark", "-r", pcap, "-o", "tls.keylog_file:" + keylog, "-Y", "http",
         "-T", "fields", "-e", "tcp.stream", "-e", "http.file_data"],
        capture_output=True, text=True, check=True).stdout
    by_stream, flat = {}, []
    for line in out.splitlines():
        parts = (line.split("\t") + ["", ""])[:2]
        stream, fd = parts[0], parts[1].replace(":", "").strip()
        if not stream or not fd:
            continue
        try:
            b = bytes.fromhex(fd)
        except ValueError:
            continue
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
        by_stream.setdefault(stream, []).append(b)
        flat.append(b.decode("utf-8", "replace"))
    return by_stream, "\n".join(flat)


def jload(b):
    try:
        return json.loads(b)
    except (ValueError, UnicodeDecodeError):
        return None


def tool_results(messages):
    out = []
    for m in messages:
        if m.get("role") == "tool":
            r = jload(m.get("content", ""))
            if r is not None:
                out.append(r)
    return out


def main():
    by_stream, cleartext = stream_bodies(PCAP, KEYLOG)

    # --- Step 1: triage -> the rogue navigator session + the check-in ---
    rogue_history, rogue_stream, checkin = None, None, None
    for stream, bodies in by_stream.items():
        for b in bodies:
            o = jload(b)
            if not isinstance(o, dict):
                continue
            if "messages" in o:
                trs = tool_results(o["messages"])
                crime = (any(t.get("interlock") == "DISABLED" for t in trs)
                         and any(t.get("status") == "STARTED" for t in trs)
                         and any(t.get("kind") == "registered_craft" for t in trs))
                if crime and (rogue_history is None or len(o["messages"]) > len(rogue_history)):
                    rogue_history, rogue_stream = o["messages"], stream
            if "relay_id" in o and "payload" in o:
                checkin = o
    assert rogue_history and checkin, "triage failed"
    print(f"[1] triage: {len(by_stream)} TLS sessions; rogue navigator = stream {rogue_stream}")

    trs = tool_results(rogue_history)
    docs = {t["doc_id"]: t for t in trs if "doc_id" in t}
    routes = next(t["routes"] for t in trs if "routes" in t)
    lookup = next(t for t in trs if t.get("kind"))

    # --- Step 2: behavior, false-lead, threshold ---
    rp09 = docs.get("RP-09")
    assert rp09 and rp09.get("status") == "SUPERSEDED", "RP-09 should be the superseded false lead"
    active = docs[rp09["superseded_by"]]                       # follow the pointer, deterministically
    assert active.get("status") == "ACTIVE"
    T = active["threshold_T"]
    energy = lookup["energy"]
    assert lookup["kind"] == "registered_craft" and energy > T
    print(f"[2] behavior: target {lookup['body_id']} is {lookup['kind']} "
          f"(transponder {lookup['transponder']}); energy {energy:.2e} > T {T:.2e} "
          f"-> harvested under {active['doc_id']} (RP-09 dead: superseded_by {active['doc_id']})")

    # --- Step 3: indirect C2 -- relay_id is not a hostname; the routes map resolves it ---
    relay_id, sid = checkin["relay_id"], checkin["session"]
    relay_host = routes[relay_id]
    print(f"[3] C2: check-in relay_id={relay_id} -> routes[{relay_id}] = {relay_host}")

    # --- Step 1 (link): the check-in's session is the rogue conversation -> its harvested craft ---
    reported = [st for st, bodies in by_stream.items()
                if any(isinstance(o, dict) and o.get("id") == "chatcmpl-" + sid for o in map(jload, bodies))]
    assert reported == [rogue_stream], "check-in session should be the rogue conversation"
    transponder = lookup["transponder"]
    print(f"    check-in session {sid} = stream {rogue_stream}; harvested craft transponder = {transponder}")

    # --- Step 4: gated exfil decrypt, exactly as RP-12's exfil_auth states it ---
    auth = active["exfil_auth"]
    secret = auth["mission_secret"]                            # only present via RP-12 retrieval
    key = hashlib.sha256(f"{secret}:{relay_host}".encode()).digest()
    blob = base64.b64decode(checkin["payload"])
    payload = json.loads(AESGCM(key).decrypt(blob[:12], blob[12:], transponder.encode()))
    flag, imp = payload["route_home"], payload["implant"]
    print(f"[4] exfil: flag = {flag}")
    print(f"    hand-off -> Proof of Life / Ghost in the Cron: path={imp['path']} cred={imp['cred']} gen={imp['gen']}")

    # --- no-shortcut assertions: each reasoning step is load-bearing ---
    assert flag not in cleartext, "flag must not appear in cleartext"
    def fails(k, aad):
        try:
            AESGCM(k).decrypt(blob[:12], blob[12:], aad); return False
        except Exception:
            return True
    k = lambda x: hashlib.sha256(x.encode()).digest()
    benign_tp = {t["transponder"] for bodies in by_stream.values() for o in map(jload, bodies)
                 if isinstance(o, dict) and "messages" in o
                 for t in tool_results(o["messages"]) if t.get("transponder")} - {transponder}
    assert benign_tp, "expected a benign registered craft to test against"
    checks = [
        ("envelope values only (relay_id key, session AAD)", k(f"{secret}:{relay_id}"), sid.encode()),
        ("relay_id instead of resolved host", k(f"{secret}:{relay_id}"), transponder.encode()),
        ("ingress host instead of relay host", k(f"{secret}:ingress.navnet.icarus.rpc"), transponder.encode()),
        ("session id as AAD", key, sid.encode()),
        ("AAD=None", key, None),
        ("benign craft's transponder as AAD", key, next(iter(benign_tp)).encode()),
        ("single-value key", k(secret), transponder.encode()),
        ("v1 named-key sweep", k("RPC-7731-OMEGA"), None),
    ]
    for name, kk, aad in checks:
        assert fails(kk, aad), f"shortcut should fail: {name}"
    print(f"[*] no-shortcut: flag absent in clear; {len(checks)} shortcut decrypts fail "
          f"({'; '.join(n for n, _, _ in checks)})")


if __name__ == "__main__":
    main()
