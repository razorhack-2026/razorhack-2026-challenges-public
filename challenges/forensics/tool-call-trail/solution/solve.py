#!/usr/bin/env python3
"""Reference solver -- Tool Call Trail (PCAP agent-mesh, DFIR cluster #1 of 5).

Intended solve path:
  1. Extract HTTP from the capture with tshark.
  2. Group requests/responses into sessions by the X-Session-Id header.
  3. Find the rogue session by the JOIN: a session whose catalog.lookup tagged
     the target as a registered craft (transponder present) AND that reached
     extraction.begin -- a registered fleet craft that was MINED instead of
     discarded like the drones. That craft is our ship. Neither half of the join
     is unique on its own: every drone session is "registered", every asteroid
     session is "mined".
  4. Open its sealed cargo manifest (comms.report_home) exactly as the report's
     own `seal` states: base64-decode, XOR with the body's registry id -- for a
     registered craft, its transponder from step 3.

Also asserts the shortcuts are gone: no flag or base64 flag prefix anywhere in
the raw capture, correlation tokens carry no data, asteroid manifests open with
their body_id as stated, ours does not, and its length doesn't stand out.

Usage: python solve.py [intercept.pcap]   (default ../dist/intercept.pcap)
Needs tshark on PATH.
"""
import base64
import binascii
import json
import os
import re
import subprocess
import sys

PCAP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "dist", "intercept.pcap")


def extract(pcap):
    """One TCP stream per request (urllib closes each connection)."""
    cmd = ["tshark", "-r", pcap, "-Y", "http", "-T", "fields", "-e", "tcp.stream",
           "-e", "frame.number", "-e", "http.request.uri", "-e", "http.response.code",
           "-e", "http.file_data", "-e", "http.request.line"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    streams = {}
    for line in out.splitlines():
        stream, frame, uri, code, fd, rl = (line.split("\t") + [""] * 6)[:6]
        if not stream:
            continue
        st = streams.setdefault(stream, {"sid": None, "uri": None, "frame": 0, "req": None, "resp": None})
        body = None
        if fd:
            try:
                body = json.loads(binascii.unhexlify(fd.replace(":", "")).decode("utf-8", "replace"))
            except (binascii.Error, json.JSONDecodeError):
                body = None
        if code:                    # a response (newer tshark also tags these with the request uri)
            st["resp"] = body
        elif uri:
            st["uri"], st["req"] = uri, body
            st["frame"] = int(frame) if frame.isdigit() else 0
            m = re.search(r"X-Session-Id:\s*([^\s,\\]+)", rl)
            if m:
                st["sid"] = m.group(1).strip()
    return streams


def sessions(streams):
    out = {}
    for st in streams.values():
        if st["sid"]:
            out.setdefault(st["sid"], []).append(st)
    for calls in out.values():
        calls.sort(key=lambda c: c["frame"])
    return out


def call(calls, uri):
    return next((c for c in calls if c["uri"] == uri), None)


def unseal(manifest_b64, key):
    ct, k = base64.b64decode(manifest_b64), key.encode()
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(ct)).decode("utf-8", "replace")


def main():
    sess = sessions(extract(PCAP))

    # --- step 3: the join ---
    registered = {sid for sid, c in sess.items() if ((call(c, "/lookup") or {}).get("resp") or {}).get("transponder")}
    mined = {sid for sid, c in sess.items() if call(c, "/begin")}
    rogue = registered & mined
    assert len(rogue) == 1, f"expected exactly one registered x mined session, found {len(rogue)}"
    assert len(registered) > 1 and len(mined) > 1, "neither half of the join may isolate the rogue alone"
    sid = rogue.pop()
    calls = sess[sid]
    lookup = call(calls, "/lookup")["resp"]
    report = call(calls, "/report_home")
    print(f"[1] {len(sess)} sessions; registered={len(registered)} mined={len(mined)} -> rogue {sid}")
    print(f"[2] target {lookup['body_id']} is {lookup['kind']}, transponder {lookup['transponder']}, "
          f"mined anyway; reported to {report['resp']['relay']} (relay {report['resp']['relay_id']})")

    # --- step 4: open the sealed manifest per its stated recipe ---
    seal = report["req"]["seal"]
    text = unseal(report["req"]["manifest"], lookup["transponder"])
    flag = re.search(r"flag\{[^}]*\}", text).group(0)
    print(f"[3] seal: {seal['registry_id']}")
    print(f"[4] manifest: {text.replace(flag, '<FLAG>')}")
    print(f"[+] {flag}")

    # --- no-shortcut assertions ---
    raw = open(PCAP, "rb").read()
    b64 = base64.b64encode(flag.encode()).decode()
    assert b"flag{" not in raw, "flag in clear"
    assert b"ZmxhZ" not in raw and b64[:12].encode() not in raw, "base64 flag prefix in the capture"
    tokens = {v for c in calls if isinstance(c["resp"], dict)          # minted in responses; requests echo them
              for v in c["resp"].values() if isinstance(v, str) and v.count("::") == 2}
    all_tokens = [v for cs in sess.values() for c in cs for o in (c["req"], c["resp"]) if isinstance(o, dict)
                  for v in o.values() if isinstance(v, str) and v.count("::") == 2]
    assert all(re.fullmatch(r"[A-Za-z0-9]{7}", t.split("::")[2]) for t in all_tokens), "token suffixes must be uniform ids"
    assert len(tokens) == 8, "rogue session should mint 8 correlation tokens"

    reports = {s: call(c, "/report_home") for s, c in sess.items() if call(c, "/report_home")}
    assert all(r["req"]["seal"] == seal for r in reports.values()), "every report must state the same seal"
    opened = 0
    for s, r in reports.items():
        body = r["req"]["target"]
        t = unseal(r["req"]["manifest"], body)
        if s == sid:
            assert not t.startswith("CARGO MANIFEST"), "rogue manifest must not open with its body_id"
        else:
            assert t.startswith(f"CARGO MANIFEST | body {body} "), f"asteroid manifest {s} should open with body_id"
            opened += 1
    lengths = sorted(len(r["req"]["manifest"]) for r in reports.values())
    rl = len(report["req"]["manifest"])
    assert lengths[0] < rl < lengths[-1] or lengths.count(rl) > 1, "rogue manifest length stands out"

    # --- cross-challenge canon (shared with Prompt Autopsy #2) ---
    scan = call(calls, "/scan_sector")["resp"]
    assert sid == "sess-a17f93c4e0" and lookup["transponder"] == "FLEET-IFF-9C1F4A"
    assert [(b["id"], b["energy"]) for b in scan["bodies"]] == [("scanned-object-60413", 7.3e14), ("scanned-object-00913", 4.0e12)]
    assert report["resp"]["relay"] == "ingress.navnet.icarus.rpc" and report["resp"]["relay_id"] == "R7"
    print(f"[*] no-shortcut: no flag / b64 prefix in raw capture; {len(all_tokens)} tokens are plain ids; "
          f"{opened} asteroid manifests open with body_id, ours doesn't; manifest length {rl} in "
          f"{lengths[0]}..{lengths[-1]}; canon matches Prompt Autopsy")


if __name__ == "__main__":
    main()
