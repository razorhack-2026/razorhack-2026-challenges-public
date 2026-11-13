import os, re, socket, struct, uuid
from pathlib import Path
def solve():
    raw=(Path(__file__).parents[1]/"dist/dock_handshake.pcap").read_bytes()
    # Extract the protocol key from captured HTTP bytes without using organizer source.
    m=re.search(rb"hmac_key=([a-z_]+)",raw)
    if not m: raise ValueError("handshake key absent from capture")
    key=m.group(1); nonce=uuid.uuid4().int & 0xffffffff
    body=b"\x01"+struct.pack("<I",nonce)
    packet=b"MICROBOT"+body+__import__("hashlib").sha256(key+body).digest()[:8]
    host=os.environ.get("DOCK_HOST","127.0.0.1"); port=int(os.environ.get("DOCK_PORT","4444"))
    with socket.create_connection((host,port),timeout=3) as s:
        banner=s.recv(128); s.sendall(packet); result=s.recv(256)
    match=re.search(rb"flag\{[^}]+\}",result)
    if not match: raise ValueError("service did not return a clearance token")
    return match.group().decode()
