"""
DOCK - Airlock Handshake

Players recover the MICROBOT frame layout from the pcap, then send a fresh
OPEN to this service. The nonce captured in the pcap is already spent.
"""
import os
import socket
import threading

from protocol import BANNER, CAPTURED_NONCE, CMD_OPEN, FRAME_LEN, parse

FLAG = os.environ.get("DOCK_FLAG", "flag{dock_h4ndsh4k3_r3pl4y3d}")
HOST = os.environ.get("DOCK_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "4444"))

# The pcap's captured OPEN nonce is always rejected. Other nonces are checked
# statelessly so one team cannot consume another team's nonce.


def _recvexact(conn: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def handle(conn: socket.socket) -> None:
    conn.settimeout(30)
    try:
        conn.sendall(BANNER)
        data = _recvexact(conn, FRAME_LEN)
        parsed = parse(data)
        if parsed is None:
            conn.sendall(b"NAK|bad_frame\n")
            return
        cmd, nonce = parsed
        if cmd != CMD_OPEN:
            conn.sendall(b"NAK|unknown_cmd\n")
            return
        if nonce == CAPTURED_NONCE:
            conn.sendall(b"REPLAY_REJECT\n")
            return
        conn.sendall(f"OK|{FLAG}\n".encode("ascii"))
    except (TimeoutError, OSError):
        return
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(16)
    print(f"dock listening on {HOST}:{PORT}", flush=True)
    while True:
        conn, _addr = sock.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
