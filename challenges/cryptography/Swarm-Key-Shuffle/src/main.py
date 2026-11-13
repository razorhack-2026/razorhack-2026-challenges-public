# GM-only live relay. Handles one Boneh-Durfee-vulnerable session per request.
import hmac
import math
import os
import secrets
import socketserver
import threading
import time
from pathlib import Path

from Crypto.Util.number import getPrime


HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', '31337'))

MODULUS_BITS = 1024
DELTA_LOW = 0.255
DELTA_HIGH = 0.265
SESSION_SECONDS = 1800
UNUSED_SESSION_SECONDS = 120
MAX_ATTEMPTS = 5
KEY_COOLDOWN_SECONDS = 3
MAX_KEYS_PER_CONNECTION = 5
MAX_TOTAL_SESSIONS = 10000
KEY_BURST = 50
KEY_REFILL_PER_SECOND = 20.0
TOKEN_BYTES = 16
SESSION_ID_BYTES = 16

BANNER = (
    'RAZORPOWER RELAY // SWARM NODE 7\n'
    'COMMANDS: KEY | AUTH <session> <token-hex> | HELP | QUIT\n'
)

sessions = {}
reservedIds = set()
stateLock = threading.Lock()


class TokenBucket:
    """Bounds global KEY issuance without identifying clients (NAT-safe)."""

    def __init__(self, capacity, refillPerSecond):
        self.capacity = capacity
        self.refillPerSecond = refillPerSecond
        self.tokens = float(capacity)
        self.updated = time.monotonic()

    def take(self):
        now = time.monotonic()
        self.tokens = min(
            self.capacity,
            self.tokens + (now - self.updated) * self.refillPerSecond,
        )
        self.updated = now

        if self.tokens < 1.0:
            return False

        self.tokens -= 1.0
        return True


keyBucket = TokenBucket(KEY_BURST, KEY_REFILL_PER_SECOND)


def parseTokenHex(raw):
    """Return canonical hex token, or None if malformed.

    Malformed input must never reach hmac.compare_digest: it raises TypeError
    for non-ASCII strings. Malformed tokens do not consume an AUTH attempt.
    """
    if raw.startswith('0x'):
        raw = raw[2:]

    if not raw or len(raw) % 2:
        return None

    try:
        bytes.fromhex(raw)
    except ValueError:
        return None

    return raw


def loadFlag():
    flagPath = os.environ.get('FLAG_FILE', '/app/flag.txt')

    if Path(flagPath).exists():
        return Path(flagPath).read_text(encoding='ascii').strip()

    return os.environ['FLAG']


FLAG = loadFlag()


def createSession():
    while True:
        p = getPrime(MODULUS_BITS // 2)
        q = getPrime(MODULUS_BITS // 2)

        if p == q:
            continue

        n = p * q

        if n.bit_length() != MODULUS_BITS:
            continue

        phi = (p - 1) * (q - 1)
        low = 1 << int(DELTA_LOW * n.bit_length())
        high = 1 << int(DELTA_HIGH * n.bit_length())
        d = (low + secrets.randbelow(high - low)) | 1

        if math.gcd(d, phi) != 1:
            continue

        e = pow(d, -1, phi)

        if e.bit_length() < n.bit_length() - 8:
            continue

        token = secrets.token_bytes(TOKEN_BYTES)
        ciphertext = pow(int.from_bytes(token, 'big'), e, n)

        return {
            'n': n,
            'e': e,
            'c': ciphertext,
            'token': token.hex(),
            'created': time.time(),
            'attempts': 0,
            'used': False,
        }


def sessionLifetime(session):
    """Unused sessions expire quickly so abandoned KEYs cannot fill the pool."""
    if session['attempts'] == 0:
        return UNUSED_SESSION_SECONDS

    return SESSION_SECONDS


def sessionExpired(session, now):
    return now - session['created'] > sessionLifetime(session)


def pruneState():
    now = time.time()

    for sessionId in list(sessions):
        if sessionExpired(sessions[sessionId], now):
            sessions.pop(sessionId, None)


def pruneLoop():
    while True:
        time.sleep(60)

        with stateLock:
            pruneState()


class RelayHandler(socketserver.StreamRequestHandler):
    def handle(self):
        address = self.client_address[0]
        self.lastKeyTime = 0
        self.keysIssued = 0
        self.wfile.write(BANNER.encode('ascii'))

        while True:
            line = self.rfile.readline(512)

            if not line:
                return

            command = line.decode('ascii', 'replace').strip()

            if not command:
                continue

            parts = command.split()
            action = parts[0].upper()

            if action in ('QUIT', 'EXIT'):
                return

            if action == 'HELP':
                self.wfile.write(BANNER.encode('ascii'))
                continue

            if action == 'KEY':
                self.handleKey(address)
                continue

            if action == 'AUTH':
                self.handleAuth(address, parts)
                continue

            self.wfile.write(b'ERROR unknown command\n')

    def handleKey(self, address):
        now = time.time()

        if now - self.lastKeyTime < KEY_COOLDOWN_SECONDS:
            self.wfile.write(b'RATE LIMITED try again shortly\n')
            return

        if self.keysIssued >= MAX_KEYS_PER_CONNECTION:
            self.wfile.write(b'TOO MANY SESSIONS open a new connection\n')
            return

        with stateLock:
            pruneState()

            if not keyBucket.take():
                self.wfile.write(b'RELAY BUSY try again shortly\n')
                return

            if len(sessions) + len(reservedIds) >= MAX_TOTAL_SESSIONS:
                self.wfile.write(b'RELAY BUSY try again shortly\n')
                return

            sessionId = secrets.token_hex(SESSION_ID_BYTES)

            while sessionId in sessions or sessionId in reservedIds:
                sessionId = secrets.token_hex(SESSION_ID_BYTES)

            # Reserve the slot and id so capacity holds while the key is
            # generated outside the lock (key generation is the slow part).
            reservedIds.add(sessionId)

        session = None

        try:
            session = createSession()
        except Exception as error:
            print(f'session generation failed: {error!r}', flush=True)
        finally:
            with stateLock:
                if session is not None:
                    sessions[sessionId] = session
                    self.lastKeyTime = now
                    self.keysIssued += 1

                reservedIds.discard(sessionId)

        if session is None:
            self.wfile.write(b'RELAY BUSY try again shortly\n')
            return

        response = (
            f'SESSION {sessionId}\n'
            f'BITS {MODULUS_BITS}\n'
            f'N 0x{session["n"]:x}\n'
            f'E 0x{session["e"]:x}\n'
            f'C 0x{session["c"]:x}\n'
            f'WINDOW {SESSION_SECONDS}\n'
            f'ATTEMPTS {MAX_ATTEMPTS}\n'
        )
        self.wfile.write(response.encode('ascii'))
        print(f'issued session {sessionId}', flush=True)

    def handleAuth(self, address, parts):
        if len(parts) != 3:
            self.wfile.write(b'ERROR usage: AUTH <session> <token-hex>\n')
            return

        sessionId = parts[1].lower()
        token = parseTokenHex(parts[2].lower())

        if token is None:
            self.wfile.write(
                b'ERROR token must be even-length hex (16 bytes)\n'
            )
            return

        with stateLock:
            session = sessions.get(sessionId)

            if session is None:
                self.wfile.write(b'REJECTED unknown or expired session\n')
                return

            if session['used']:
                self.wfile.write(b'REJECTED session already closed\n')
                return

            if sessionExpired(session, time.time()):
                sessions.pop(sessionId, None)
                self.wfile.write(b'REJECTED session expired\n')
                return

            session['attempts'] += 1

            if session['attempts'] > MAX_ATTEMPTS:
                sessions.pop(sessionId, None)
                self.wfile.write(b'REJECTED attempt limit reached; session closed\n')
                return

            if hmac.compare_digest(token, session['token']):
                session['used'] = True
                sessions.pop(sessionId, None)
                response = f'ACCEPTED {FLAG}\n'
                print(f'session {sessionId} accepted', flush=True)
            else:
                remaining = MAX_ATTEMPTS - session['attempts']
                response = f'REJECTED wrong token; attempts left {remaining}\n'

        self.wfile.write(response.encode('ascii'))


class RelayServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


def main():
    threading.Thread(target=pruneLoop, daemon=True).start()

    with RelayServer((HOST, PORT), RelayHandler) as server:
        print(f'relay listening on {HOST}:{PORT}', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

