"""Shared MICROBOT docking frame codec. Used by the live service and the pcap generator."""
import hashlib
import struct

MAGIC = b"MICROBOT"
KEY = b"dock_reliant"
CMD_OPEN = 0x01
CAPTURED_NONCE = 0x00001234
FRAME_LEN = 21  # 8 magic + 1 cmd + 4 nonce + 8 hmac
BANNER = b"RELIANT // DOCK\n"


def frame(cmd: int, nonce_int: int) -> bytes:
    nonce = struct.pack("<I", nonce_int & 0xFFFFFFFF)
    body = bytes([cmd]) + nonce
    mac = hashlib.sha256(KEY + body).digest()[:8]
    return MAGIC + body + mac


def parse(data: bytes) -> tuple[int, int] | None:
    if len(data) != FRAME_LEN or data[:8] != MAGIC:
        return None
    cmd = data[8]
    nonce = struct.unpack("<I", data[9:13])[0]
    mac = data[13:21]
    expect = hashlib.sha256(KEY + data[8:13]).digest()[:8]
    if mac != expect:
        return None
    return cmd, nonce
