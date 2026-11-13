#!/usr/bin/env python3
"""Seed corewatch.db — the loot a player finds after React2Shell RCE.

Two things live here, and BOTH are recovered only by cracking a credential —
never by the RCE alone:

  users        : only the MD5 *hashes* are shipped. Exactly one row cracks
                 against rockyou (j.reyes, role=engineer -> "supernova1"); admin
                 and the service account get random 32-hex digests that never
                 crack, so there's no ambiguity about the way forward. The
                 cracked password is reused as the SSH login on eng-ws.

  rtu_secrets  : one openssl-AES-256-CBC (pbkdf2) blob, base64'd. It is the
                 engineer's "RTU maintenance override memo" encrypted WITH THAT
                 SAME PASSWORD. Cracking the hash lets you decrypt the memo. The
                 base64 begins `U2FsdGVk` (openssl "Salted__"), which signposts
                 the method. The PLAINTEXT memo never ships in the image — only
                 this ciphertext — so a shell alone yields nothing here.

usage: seed_db.py <db> [<memo_file> <encrypt_password>]
       (memo args optional so the script still works standalone; the Dockerfile
        passes them, then deletes the plaintext memo)
"""
import os, sqlite3, sys, datetime, random, base64, subprocess

DB = sys.argv[1] if len(sys.argv) > 1 else "corewatch.db"
MEMO = sys.argv[2] if len(sys.argv) > 2 else None
ENCPW = sys.argv[3] if len(sys.argv) > 3 else None

# md5("supernova1") — the intended crack; plaintext is NOT stored here.
J_REYES_MD5 = "4e9bcf545ca815d8b665081bb0a42aa5"

users = [
    ("admin",       os.urandom(16).hex(), "administrator"),   # never cracks
    ("svc_monitor", os.urandom(16).hex(), "service"),         # never cracks
    ("j.reyes",     J_REYES_MD5,          "engineer"),        # cracks -> reused SSH cred
]

if os.path.exists(DB):
    os.remove(DB)
c = sqlite3.connect(DB)
c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password_md5 TEXT, role TEXT)")
c.executemany("INSERT INTO users (username, password_md5, role) VALUES (?,?,?)", users)

c.execute("CREATE TABLE sensor_logs (id INTEGER PRIMARY KEY, ts TEXT, channel TEXT, value REAL)")
rows = []
base = datetime.datetime(2027, 3, 14, 6, 0, 0)
for i in range(60):
    t = (base + datetime.timedelta(minutes=i)).isoformat()
    for ch, lo, hi in (("core_temp_k",305,320),("coolant_flow",4.2,5.1),("extraction_pct",88,99)):
        rows.append((t, ch, round(random.uniform(lo, hi), 2)))
c.executemany("INSERT INTO sensor_logs (ts, channel, value) VALUES (?,?,?)", rows)

# rtu_secrets — engineer memo, encrypted with the reused password.
c.execute("CREATE TABLE rtu_secrets (id INTEGER PRIMARY KEY, label TEXT, blob TEXT)")
if MEMO and ENCPW:
    ct = subprocess.check_output(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "10000",
         "-md", "sha256", "-salt", "-in", MEMO, "-pass", "pass:" + ENCPW])
    blob = base64.b64encode(ct).decode()
    c.execute("INSERT INTO rtu_secrets (label, blob) VALUES (?,?)",
              ("RTU maintenance override memo (encrypted; engineer key)", blob))

c.commit(); c.close()
print(f"seeded {DB}: {len(users)} users, {len(rows)} sensor_logs rows"
      + (", 1 rtu_secrets blob" if (MEMO and ENCPW) else ""))
