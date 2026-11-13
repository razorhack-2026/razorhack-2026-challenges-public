#!/usr/bin/env python3
"""DOCK artifact generator. Writes dist/dock_handshake.pcap.

Three conversations:
  1. Captured OPEN - accepted in the capture; its nonce is reserved by the live service
  2. Microbot replay of the same frame - REPLAY_REJECT
  3. HTTP decoy that leaks only the key needed to recover the frame format

The live service on tcp/4444 is what returns the real flag for a fresh nonce.
"""
import os
import socket
import struct

from protocol import BANNER, CAPTURED_NONCE, CMD_OPEN, frame

CLIENT_IP = "10.0.4.10"
DOCK_IP = "10.0.4.2"
HTTP_IP = "10.0.4.80"
CLIENT_MAC = bytes.fromhex("02000000000a")
DOCK_MAC = bytes.fromhex("020000000002")
HTTP_MAC = bytes.fromhex("020000000050")



def _u16(n: int) -> bytes:
    return struct.pack("!H", n)


def _u32(n: int) -> bytes:
    return struct.pack("!I", n)


def _checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += int.from_bytes(data[i : i + 2], "big")
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def _ipv4(src: str, dst: str, payload: bytes) -> bytes:
    header = bytearray(
        b"\x45\x00"
        + _u16(20 + len(payload))
        + b"\x00\x00\x40\x00\x40\x06\x00\x00"
        + socket.inet_aton(src)
        + socket.inet_aton(dst)
    )
    header[10:12] = _u16(_checksum(header))
    return bytes(header) + payload


def _tcp(src: str, sport: int, dst: str, dport: int, seq: int, ack: int, flags: int, payload: bytes) -> bytes:
    offset_flags = (5 << 12) | flags
    header = bytearray(
        _u16(sport)
        + _u16(dport)
        + _u32(seq)
        + _u32(ack)
        + _u16(offset_flags)
        + _u16(8192)
        + b"\x00\x00\x00\x00"
    )
    pseudo = (
        socket.inet_aton(src)
        + socket.inet_aton(dst)
        + b"\x00\x06"
        + _u16(20 + len(payload))
    )
    header[16:18] = _u16(_checksum(pseudo + header + payload))
    return bytes(header) + payload


def _eth(dst_mac: bytes, src_mac: bytes, payload: bytes) -> bytes:
    return dst_mac + src_mac + b"\x08\x00" + payload


def _conversation(
    client_ip: str,
    server_ip: str,
    sport: int,
    dport: int,
    c_mac: bytes,
    s_mac: bytes,
    server_first: bytes,
    request: bytes,
    response: bytes,
    t0: float,
    cseq: int,
    sseq: int,
) -> list[tuple[float, bytes]]:
    syn, syn_ack, ack, psh_ack = 0x02, 0x12, 0x10, 0x18
    packets: list[tuple[float, bytes]] = []
    t = t0

    def add(src_ip, dst_ip, smac, dmac, sp, dp, seq, ackn, flags, payload):
        nonlocal t
        frame_bytes = _eth(
            dmac,
            smac,
            _ipv4(src_ip, dst_ip, _tcp(src_ip, sp, dst_ip, dp, seq, ackn, flags, payload)),
        )
        packets.append((t, frame_bytes))
        t += 0.001

    add(client_ip, server_ip, c_mac, s_mac, sport, dport, cseq, 0, syn, b"")
    cseq += 1
    add(server_ip, client_ip, s_mac, c_mac, dport, sport, sseq, cseq, syn_ack, b"")
    sseq += 1
    add(client_ip, server_ip, c_mac, s_mac, sport, dport, cseq, sseq, ack, b"")

    if server_first:
        t += 0.008
        add(server_ip, client_ip, s_mac, c_mac, dport, sport, sseq, cseq, psh_ack, server_first)
        sseq += len(server_first)

    t += 0.008
    add(client_ip, server_ip, c_mac, s_mac, sport, dport, cseq, sseq, psh_ack, request)
    cseq += len(request)
    t += 0.008
    add(server_ip, client_ip, s_mac, c_mac, dport, sport, sseq, cseq, psh_ack, response)
    return packets


def _pcap_global() -> bytes:
    return struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)


def _pcap_pkt(ts: float, data: bytes) -> bytes:
    sec = int(ts)
    usec = int((ts - sec) * 1_000_000)
    return struct.pack("<IIII", sec, usec, len(data), len(data)) + data


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
    os.makedirs(out_dir, exist_ok=True)

    open_frame = frame(CMD_OPEN, CAPTURED_NONCE)
    packets: list[tuple[float, bytes]] = []

    packets.extend(
        _conversation(
            CLIENT_IP,
            DOCK_IP,
            41000,
            4444,
            CLIENT_MAC,
            DOCK_MAC,
            BANNER,
            open_frame,
            b"OK|bay=3|note=nonce_spent\n",
            t0=1_724_400_000.0,
            cseq=1000,
            sseq=2000,
        )
    )
    packets.extend(
        _conversation(
            CLIENT_IP,
            DOCK_IP,
            41001,
            4444,
            CLIENT_MAC,
            DOCK_MAC,
            BANNER,
            open_frame,
            b"REPLAY_REJECT\n",
            t0=1_724_400_010.0,
            cseq=3000,
            sseq=4000,
        )
    )

    http_req = b"GET /dock.conf HTTP/1.0\r\nHost: dock-internal\r\n\r\n"
    http_resp = (
        b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\n"
        b"# RELIANT dock config\n"
        b"hmac_key=dock_reliant\n"
        b"listen=0.0.0.0:4444\n"
    )
    packets.extend(
        _conversation(
            CLIENT_IP,
            HTTP_IP,
            41002,
            80,
            CLIENT_MAC,
            HTTP_MAC,
            b"",
            http_req,
            http_resp,
            t0=1_724_400_005.0,
            cseq=5000,
            sseq=6000,
        )
    )

    packets.sort(key=lambda item: item[0])
    out_path = os.path.join(out_dir, "dock_handshake.pcap")
    with open(out_path, "wb") as f:
        f.write(_pcap_global())
        for ts, data in packets:
            f.write(_pcap_pkt(ts, data))

    print(f"wrote dist/dock_handshake.pcap ({os.path.getsize(out_path):,} bytes, {len(packets)} packets)")
    print(f"captured OPEN nonce=0x{CAPTURED_NONCE:08x} frame={open_frame.hex()}")
    print("real flag is only on the live service, for a fresh nonce")


if __name__ == "__main__":
    main()
