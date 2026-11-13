#!/usr/bin/env python3
"""
Ghost Command -- step 1 of the reference solve.

Run this on your OWN machine, against the downloaded dist/ pcap. It needs
no network access and nothing from the jump box. It finds the one genuine
GOOSE trip frame in the capture (test/simulation == False, trip boolean ==
True -- every other trip-shaped frame is either a rehearsal or a decoy from
the breaker's own position control block) and prints its raw bytes as a hex
string. Feed that hex string to replay.py on the jump box.

Usage:
    python3 find_frame.py substation_test_window.pcap
"""

import struct
import sys

from scapy.all import rdpcap

ETHERTYPE_GOOSE = 0x88B8
TAG_GOCB_REF = 0x80
TAG_DATSET = 0x82
TAG_STNUM = 0x85
TAG_SQNUM = 0x86
TAG_TEST = 0x87
TAG_ALLDATA = 0xAB
TAG_GOOSE_PDU = 0x61
TAG_DATA_BOOLEAN = 0x83

TRIP_GOCB_REF = "IED_PROT03LLN0$GO$gcbTrip"


def _read_tlv(buf, offset):
    tag = buf[offset]
    length_byte = buf[offset + 1]
    if length_byte & 0x80:
        n = length_byte & 0x7F
        length = int.from_bytes(buf[offset + 2:offset + 2 + n], "big")
        value_start = offset + 2 + n
    else:
        length = length_byte
        value_start = offset + 2
    value = buf[value_start:value_start + length]
    return tag, value, value_start + length


def _decode_integer(b):
    return int.from_bytes(b, "big", signed=True)


def parse_goose_frame(raw):
    if len(raw) < 22:
        return None
    ethertype = struct.unpack(">H", raw[12:14])[0]
    if ethertype != ETHERTYPE_GOOSE:
        return None

    _appid, length, _r1, _r2 = struct.unpack(">HHHH", raw[14:22])
    pdu = raw[22:14 + length]
    if not pdu or pdu[0] != TAG_GOOSE_PDU:
        return None

    _tag, body, _end = _read_tlv(pdu, 0)

    fields = {}
    all_data = []
    off = 0
    while off < len(body):
        tag, value, off = _read_tlv(body, off)
        if tag == TAG_ALLDATA:
            inner = 0
            while inner < len(value):
                dtag, dval, inner = _read_tlv(value, inner)
                if dtag == TAG_DATA_BOOLEAN:
                    all_data.append(dval != b"\x00")
                else:
                    all_data.append(dval)
        else:
            fields[tag] = value

    return {
        "gocb_ref": fields.get(TAG_GOCB_REF, b"").decode("ascii", "replace"),
        "st_num": _decode_integer(fields.get(TAG_STNUM, b"\x00")),
        "sq_num": _decode_integer(fields.get(TAG_SQNUM, b"\x00")),
        "test": fields.get(TAG_TEST, b"\x00") != b"\x00",
        "data_values": all_data,
        "raw": raw,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: find_frame.py <pcap-path>")

    pkts = rdpcap(sys.argv[1])
    candidates = []
    for pkt in pkts:
        frame = parse_goose_frame(bytes(pkt))
        if frame is None or frame["gocb_ref"] != TRIP_GOCB_REF:
            continue
        if not frame["data_values"] or frame["data_values"][0] is not True:
            continue
        candidates.append(frame)

    genuine = [f for f in candidates if not f["test"]]
    print(f"[+] {len(candidates)} trip=True frames on {TRIP_GOCB_REF}, "
          f"{len(genuine)} with simulation/test=False", file=sys.stderr)
    if len(genuine) != 1:
        raise SystemExit("expected exactly one genuine frame, found "
                          f"{len(genuine)} -- capture may be wrong")

    f = genuine[0]
    print(f"[+] genuine frame: stNum={f['st_num']} sqNum={f['sq_num']} "
          f"({len(f['raw'])} bytes)", file=sys.stderr)
    print(f["raw"].hex())


if __name__ == "__main__":
    main()
