#!/usr/bin/env python3
"""Power-Trip reference solution.

Sets up the rig's scope, captures traces off the live board, recovers the
16-byte interlock key by correlation power analysis on the round-1 S-box
output, then unseals dist/interlock.enc.

The scope settings are the whole game: the target's authentication routine is
~3960 samples long, the scope holds 1024, and the cipher does not start until
~1530. Capture the wrong window and CPA returns nothing.

    python solve.py --host 127.0.0.1 --port 1337

Competitors get only dist/interlock.enc; the rig documents its own command set
over the link. The client is written here from what the banner and HELP report,
so everything below is reachable from what they are given. Captures are cached
in --traces so repeat runs skip the slow part. This never reads src/.
"""
import argparse
import base64
import hashlib
import heapq
import os
import pathlib
import socket
import sys
import time

import numpy as np
from Crypto.Cipher import AES

HERE = pathlib.Path(__file__).resolve().parent
DIST = HERE.parent / "dist"

BATCH_MAX = 500          # the cap the rig reports in HELP

SBOX = np.frombuffer(bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6426841992d0fb054bb16"
), dtype=np.uint8)

HW = np.array([bin(i).count("1") for i in range(256)], dtype=np.float64)


# ------------------------------------------------------------------ transport

class Link:
    """Line-oriented link to the rig, over TCP or a local serial device."""

    def __init__(self, sock=None, serial_port=None):
        self._f = sock.makefile("rwb") if serial_port is None else serial_port

    @classmethod
    def connect(cls, host, port, serial_path, timeout=30.0):
        if serial_path:
            try:
                import serial
            except ImportError:
                sys.exit("--serial needs pyserial:  pip install pyserial")
            try:
                return cls(serial_port=serial.Serial(serial_path,
                                                    timeout=timeout))
            except Exception as exc:
                sys.exit(f"cannot open serial device {serial_path}: {exc}")
        try:
            return cls(sock=socket.create_connection((host, port),
                                                     timeout=timeout))
        except socket.gaierror:
            sys.exit(f"cannot resolve host {host!r} -- check the address "
                     f"(a plain IP like 127.0.0.1 needs all four octets)")
        except (ConnectionRefusedError, TimeoutError, OSError) as exc:
            sys.exit(f"cannot reach the rig at {host}:{port} ({exc}).\n"
                     f"Is it running?  docker compose up -d")

    def readline(self):
        return self._f.readline().decode("utf-8", "replace").strip()

    def send(self, line):
        self._f.write((line + "\r\n").encode())
        self._f.flush()

    def skip_banner(self):
        line = self.readline()
        while line and not line.startswith("Type HELP"):
            line = self.readline()


def parse_capture(line):
    parts = line.split()
    if len(parts) != 4 or parts[0] != "CAP":
        return None
    _, pt_hex, ct_hex, b64 = parts
    return (
        np.frombuffer(bytes.fromhex(pt_hex), dtype=np.uint8),
        np.frombuffer(bytes.fromhex(ct_hex), dtype=np.uint8),
        np.frombuffer(base64.b64decode(b64), dtype=np.int8),
    )


def load_cache(path):
    if not path.exists():
        return [], [], []
    try:
        d = np.load(path)
        return list(d["traces"]), list(d["plaintexts"]), list(d["ciphertexts"])
    except Exception:
        return [], [], []


def save_cache(path, traces, pts, cts):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        np.savez_compressed(fh, traces=np.asarray(traces),
                            plaintexts=np.asarray(pts),
                            ciphertexts=np.asarray(cts))
    os.replace(tmp, path)


def configure_scope(link, samples, offset, gain_db):
    """Set the capture up before collecting anything.

    The scope powers up at -40 dB, 256 samples, offset 0 -- below the usable
    gain floor, and windowed onto the frame-staging work that runs before the
    cipher. Every one of these has to be changed or the capture is worthless.
    """
    for cmd in (f"SCOPE SET GAIN {gain_db}",
                f"SCOPE SET SAMPLES {samples}",
                f"SCOPE SET OFFSET {offset}"):
        link.send(cmd)
        reply = link.readline()
        if reply.startswith("ERR"):
            sys.exit(f"scope rejected {cmd!r}: {reply}")
    link.send("SCOPE")
    print(f"[*] {link.readline()}")


def collect(host, port, serial, count, path, samples, offset, gain_db):
    """Top the cache up to `count` captures.

    The rig is deterministic per plaintext, so a dropped link costs nothing --
    reconnect and keep going from what is already on disk.
    """
    traces, pts, cts = load_cache(path)
    need = count - len(traces)
    if need <= 0:
        print(f"[*] using {len(traces)} cached captures from {path.name}")
        return np.asarray(traces), np.asarray(pts), np.asarray(cts)

    print(f"[*] capturing {need} traces from the rig")
    link = Link.connect(host, port, serial)
    link.skip_banner()
    configure_scope(link, samples, offset, gain_db)

    t0 = time.time()
    got = 0
    while got < need:
        want = min(BATCH_MAX, need - got)
        link.send(f"BATCH {want}")
        while True:
            line = link.readline()
            if not line:
                raise ConnectionError("link closed mid-batch")
            if line.startswith("END"):
                break
            if line.startswith("ERR"):
                sys.exit(f"rig error: {line}")
            rec = parse_capture(line)
            if rec is None:
                continue
            pts.append(rec[0]); cts.append(rec[1]); traces.append(rec[2])
            got += 1
        print(f"\r    {len(traces)} captures", end="", flush=True)
        save_cache(path, traces, pts, cts)
    print(f"\n[*] capture took {time.time() - t0:.1f}s")

    return np.asarray(traces), np.asarray(pts), np.asarray(cts)


# ------------------------------------------------------------------ analysis

def cpa(traces, pts, window, keep=6):
    """Correlate HW(SBox(p ^ k)) against every sample, for each key byte.

    Returns, per byte, the top `keep` (candidate, correlation) pairs best
    first. Keeping more than the winner matters: near the trace-count threshold
    the right byte routinely places second to sixth, and enumerating those is
    far cheaper than capturing thousands more traces.
    """
    t = traces[:, :window].astype(np.float64)
    t -= t.mean(axis=0)
    tss = np.sqrt((t ** 2).sum(axis=0))
    tss[tss == 0] = 1e-12

    cands = []
    for b in range(16):
        pb = pts[:, b].astype(np.uint8)
        peaks = np.zeros(256)
        for k in range(256):
            h = HW[SBOX[pb ^ k]]
            h = h - h.mean()
            hss = np.sqrt((h ** 2).sum())
            if hss == 0:
                continue
            peaks[k] = float(np.abs((h @ t) / (hss * tss)).max())
        order = np.argsort(peaks)[::-1][:keep]
        cands.append([(int(k), float(peaks[k])) for k in order])
    return cands


def candidate_keys(cands, limit=200_000):
    """Yield keys in increasing order of total correlation penalty.

    Textbook key enumeration. Each byte's candidates carry a penalty of
    (best correlation - this candidate's correlation); the best-first search
    walks the combinations cheapest-total-penalty first, so the most plausible
    keys are tried long before the implausible ones. Cheap next to a trial
    decrypt, and it rescues a CPA result that is a few bytes short.
    """
    pen = [[c[0][1] - s for _, s in c] for c in cands]
    start = (0,) * 16
    seen = {start}
    heap = [(0.0, start)]
    produced = 0

    while heap and produced < limit:
        total, idx = heapq.heappop(heap)
        yield bytes(cands[b][idx[b]][0] for b in range(16))
        produced += 1
        for b in range(16):
            if idx[b] + 1 < len(cands[b]):
                nxt = idx[:b] + (idx[b] + 1,) + idx[b + 1:]
                if nxt not in seen:
                    seen.add(nxt)
                    heapq.heappush(
                        heap,
                        (total - pen[b][idx[b]] + pen[b][idx[b] + 1], nxt))


def payload_of(blob):
    return blob.split(b"\n--\n", 1)[1] if b"\n--\n" in blob else blob


def header_matches(payload, device_key):
    """Cheap test for key enumeration: decrypt one block, check the header."""
    sealing_key = hashlib.sha256(device_key).digest()[:16]
    first = AES.new(sealing_key, AES.MODE_CBC,
                    payload[:16]).decrypt(payload[16:32])
    return first.startswith(b"RPC-INTERLOCK-AU")


def unseal(blob, device_key):
    """Undo the envelope the blob describes: sha256 key, CBC, IV first."""
    payload = payload_of(blob)
    sealing_key = hashlib.sha256(device_key).digest()[:16]
    iv, ct = payload[:16], payload[16:]
    pt = AES.new(sealing_key, AES.MODE_CBC, iv).decrypt(ct)
    if not pt.startswith(b"RPC-INTERLOCK-AUTH"):
        return None
    return pt[:-pt[-1]].decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1337)
    ap.add_argument("--serial", default=None,
                    help="serial device instead of host/port")
    ap.add_argument("-n", "--count", type=int, default=6000)
    # Scope setup. The routine runs ~3960 samples; frame staging and the CRC
    # fill the first ~1530, so a capture has to start after that to see round 1
    # (the S-box leak lands near sample 1643). Depth is capped at 1024.
    ap.add_argument("--samples", type=int, default=1024, help="capture depth")
    ap.add_argument("--offset", type=int, default=1600,
                    help="samples to skip after the trigger")
    ap.add_argument("--gain", type=float, default=0.0, help="scope gain in dB")
    ap.add_argument("--traces", default=str(HERE / "traces.npz"))
    ap.add_argument("--blob", default=str(DIST / "interlock.enc"))
    args = ap.parse_args()

    traces, pts, _ = collect(args.host, args.port, args.serial,
                             args.count, pathlib.Path(args.traces),
                             args.samples, args.offset, args.gain)
    print(f"[*] {traces.shape[0]} traces x {traces.shape[1]} samples")

    t0 = time.time()
    cands = cpa(traces, pts, traces.shape[1])
    tops = [c[0][1] for c in cands]
    print(f"[*] CPA in {time.time() - t0:.1f}s")
    print(f"[*] per-byte peak correlation "
          f"{min(tops):.3f} .. {max(tops):.3f}")

    blob = pathlib.Path(args.blob).read_bytes()
    payload = payload_of(blob)
    t0 = time.time()
    key = None
    for tried, guess in enumerate(candidate_keys(cands), 1):
        if header_matches(payload, guess):
            key = guess
            break
    if key is not None and tried > 1:
        print(f"[*] top CPA key was short; key enumeration found it after "
              f"{tried} candidates in {time.time() - t0:.1f}s")
    record = unseal(blob, key) if key is not None else None

    if key is None:
        print(f"[!] no candidate key unseals interlock.enc. CPA is short of "
              f"the threshold at {traces.shape[0]} traces.\n"
              f"[!] Captures are cached, so re-running as-is will reuse them "
              f"and fail identically -- raise the count instead:\n"
              f"[!]     python solve.py -n {traces.shape[0] + 2000}",
              file=sys.stderr)
        return 1
    print(f"[*] interlock key = {key.hex()}")

    print()
    print(record.strip())
    flag = [l.split("auth: ", 1)[1] for l in record.splitlines()
            if l.startswith("auth: ")]
    if flag:
        print()
        print(f"FLAG: {flag[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
