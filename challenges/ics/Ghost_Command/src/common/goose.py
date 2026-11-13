"""
Minimal IEC 61850-8-1 GOOSE encoder/decoder.

Not a general ASN.1/BER library -- just enough hand-rolled BER-TLV to build
and parse a GOOSE APDU for this challenge, matching real wire format closely
enough that Wireshark's built-in GOOSE dissector renders it correctly.

Frame layout (no VLAN tag, kept flat for this challenge):

    dst MAC (6) | src MAC (6) | EtherType 0x88B8 (2) |
    APPID (2) | Length (2) | Reserved1 (2) | Reserved2 (2) |
    goosePdu (BER, tag 0x61, constructed)

goosePdu fields, in order, each a context-tagged BER TLV:
    [0] gocbRef            VisibleString
    [1] timeAllowedtoLive  INTEGER
    [2] datSet             VisibleString
    [3] goID               VisibleString
    [4] t                  UtcTime (8 bytes: 4B epoch seconds, 3B fraction, 1B quality)
    [5] stNum              INTEGER
    [6] sqNum              INTEGER
    [7] test               BOOLEAN
    [8] confRev            INTEGER
    [9] ndsCom             BOOLEAN
    [10] numDatSetEntries  INTEGER
    [11] allData           SEQUENCE OF Data (tag 0xAB, constructed)
         -- each entry here is a plain MMS Data boolean: tag 0x83
"""

import struct
import time

ETHERTYPE_GOOSE = 0x88B8

TAG_GOCB_REF = 0x80
TAG_TIME_ALLOWED = 0x81
TAG_DATSET = 0x82
TAG_GOID = 0x83
TAG_T = 0x84
TAG_STNUM = 0x85
TAG_SQNUM = 0x86
TAG_TEST = 0x87
TAG_CONFREV = 0x88
TAG_NDSCOM = 0x89
TAG_NUM_ENTRIES = 0x8A
TAG_ALLDATA = 0xAB
TAG_GOOSE_PDU = 0x61

TAG_DATA_BOOLEAN = 0x83  # MMS Data CHOICE, boolean member, context tag 3


def encode_length(n):
    if n < 0x80:
        return bytes([n])
    enc = b""
    while n:
        enc = bytes([n & 0xFF]) + enc
        n >>= 8
    return bytes([0x80 | len(enc)]) + enc


def encode_tlv(tag, value):
    return bytes([tag]) + encode_length(len(value)) + value


def encode_integer(tag, value):
    if value == 0:
        body = b"\x00"
    else:
        body = value.to_bytes((value.bit_length() + 8) // 8, "big", signed=True)
    return encode_tlv(tag, body)


def encode_boolean(tag, value):
    return encode_tlv(tag, b"\xff" if value else b"\x00")


def encode_visible_string(tag, s):
    return encode_tlv(tag, s.encode("ascii"))


def encode_utctime(tag, when=None):
    when = when if when is not None else time.time()
    secs = int(when)
    frac = when - secs
    frac_24 = int(frac * (1 << 24)) & 0xFFFFFF
    quality = 0x0A  # leap-seconds-known + clock-failure=0 + clock-not-sync=0, low accuracy bits
    body = struct.pack(">I", secs) + frac_24.to_bytes(3, "big") + bytes([quality])
    return encode_tlv(tag, body)


def encode_all_data_booleans(values):
    body = b"".join(encode_boolean(TAG_DATA_BOOLEAN, v) for v in values)
    return encode_tlv(TAG_ALLDATA, body)


def build_goose_apdu(gocb_ref, dat_set, go_id, st_num, sq_num, test,
                      data_values, time_allowed=2000, conf_rev=1,
                      nds_com=False, when=None):
    """Build the goosePdu BER content (fields [0]..[11])."""
    fields = b"".join([
        encode_visible_string(TAG_GOCB_REF, gocb_ref),
        encode_integer(TAG_TIME_ALLOWED, time_allowed),
        encode_visible_string(TAG_DATSET, dat_set),
        encode_visible_string(TAG_GOID, go_id),
        encode_utctime(TAG_T, when),
        encode_integer(TAG_STNUM, st_num),
        encode_integer(TAG_SQNUM, sq_num),
        encode_boolean(TAG_TEST, test),
        encode_integer(TAG_CONFREV, conf_rev),
        encode_boolean(TAG_NDSCOM, nds_com),
        encode_integer(TAG_NUM_ENTRIES, len(data_values)),
        encode_all_data_booleans(data_values),
    ])
    return encode_tlv(TAG_GOOSE_PDU, fields)


def build_goose_frame(dst_mac, src_mac, appid, pdu_bytes):
    """Wrap a goosePdu into the full GOOSE header + Ethernet frame (no VLAN)."""
    header = struct.pack(">HHHH", appid, 8 + len(pdu_bytes), 0, 0)
    payload = header + pdu_bytes
    eth = dst_mac + src_mac + struct.pack(">H", ETHERTYPE_GOOSE) + payload
    return eth


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------

class GooseFrame:
    def __init__(self, dst_mac, src_mac, appid, gocb_ref, time_allowed, dat_set,
                 go_id, t_secs, t_frac, st_num, sq_num, test, conf_rev,
                 nds_com, num_entries, data_values, raw):
        self.dst_mac = dst_mac
        self.src_mac = src_mac
        self.appid = appid
        self.gocb_ref = gocb_ref
        self.time_allowed = time_allowed
        self.dat_set = dat_set
        self.go_id = go_id
        self.t_secs = t_secs
        self.t_frac = t_frac
        self.st_num = st_num
        self.sq_num = sq_num
        self.test = test
        self.conf_rev = conf_rev
        self.nds_com = nds_com
        self.num_entries = num_entries
        self.data_values = data_values
        self.raw = raw  # full raw Ethernet frame bytes, for replay


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
    """Parse a raw Ethernet frame; return a GooseFrame, or None if it isn't
    a GOOSE frame this parser understands."""
    if len(raw) < 22:
        return None
    dst_mac = raw[0:6]
    src_mac = raw[6:12]
    ethertype = struct.unpack(">H", raw[12:14])[0]
    if ethertype != ETHERTYPE_GOOSE:
        return None

    appid, length, _r1, _r2 = struct.unpack(">HHHH", raw[14:22])
    pdu = raw[22:14 + length]  # length counts from APPID (offset 14)

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

    t_raw = fields.get(TAG_T, b"\x00" * 8)
    t_secs = struct.unpack(">I", t_raw[0:4])[0] if len(t_raw) >= 4 else 0
    t_frac = int.from_bytes(t_raw[4:7], "big") if len(t_raw) >= 7 else 0

    return GooseFrame(
        dst_mac=dst_mac,
        src_mac=src_mac,
        appid=appid,
        gocb_ref=fields.get(TAG_GOCB_REF, b"").decode("ascii", "replace"),
        time_allowed=_decode_integer(fields.get(TAG_TIME_ALLOWED, b"\x00")),
        dat_set=fields.get(TAG_DATSET, b"").decode("ascii", "replace"),
        go_id=fields.get(TAG_GOID, b"").decode("ascii", "replace"),
        t_secs=t_secs,
        t_frac=t_frac,
        st_num=_decode_integer(fields.get(TAG_STNUM, b"\x00")),
        sq_num=_decode_integer(fields.get(TAG_SQNUM, b"\x00")),
        test=fields.get(TAG_TEST, b"\x00") != b"\x00",
        conf_rev=_decode_integer(fields.get(TAG_CONFREV, b"\x00")),
        nds_com=fields.get(TAG_NDSCOM, b"\x00") != b"\x00",
        num_entries=_decode_integer(fields.get(TAG_NUM_ENTRIES, b"\x00")),
        data_values=all_data,
        raw=raw,
    )
