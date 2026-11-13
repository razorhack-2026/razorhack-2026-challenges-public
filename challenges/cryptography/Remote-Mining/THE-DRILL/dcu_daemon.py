#!/usr/bin/env python3
"""
DCU daemon - serves one Drill Containment Unit over a Unix socket.

Runs as the unprivileged 'drill' user, so players can see the process in ps
but cannot read anything in /opt/dcu. The kernel tells us which user is on the
other end of the socket (SO_PEERCRED), so a team cannot spoof its progress.
Units unlock in order: unit N opens once the team has mined unit N-1, unless
DCU_UNGATED lists it.

Units 1-2 run their challenge as a subprocess per connection. Unit 3 is a
competition shared by every team, so its daemon loads crypto_level3.py and runs
each session in-process (see Competition in that file).

Protocol: the client sends one line, then the daemon replies and closes.
    STATUS     -> LOCKED, ONLINE or MINED (unit 3: ONLINE/SEALED plus next hash time).
    ENTER      -> if unlocked, runs the unit's challenge on the socket. For units
                  1-2, exit status 0 marks the unit as mined.
    SCORE      -> unit 3 only: the team's score and rank.
    SCOREBOARD -> unit 3 only: standings and recent blocks.
    CODE <x>   -> developer cheat, dev deployment only: if x is the dev code and
                  the caller is a dev team, toggles a bypass of the unit locks
                  for that team (progress is not marked as mined). Anyone else,
                  and everyone on a production deployment, gets an empty reply.

Usage (normally started by entrypoint.sh):
    python3 dcu_daemon.py <unit>
"""

import importlib.util
import os
import pwd
import socket
import struct
import subprocess
import sys
import threading

UNITS = {1: "crypto.py", 2: "crypto_level2.py", 3: "crypto_level3.py"}
UNIT_NAMES = {1: "Termite-01", 2: "Dog-02", 3: "Mole-03"}
COMPETITIVE_UNIT = 3
CODE_DIR = os.environ.get("DCU_CODE_DIR", "/opt/dcu")
SOCKET_DIR = os.environ.get("DCU_SOCKET_DIR", "/run/dcu")
PROGRESS_DIR = os.environ.get("DCU_PROGRESS_DIR", "/var/lib/dcu")
# Units open without the one before them mined (entrypoint.sh: DCU_UNGATED). The
# shared Mole-03 server runs unit 3 alone, gated by the scoreboard (CTFd) instead.
UNGATED = {int(u) for u in os.environ.get("DCU_UNGATED", "").split() if u.isdigit()}
# sys.executable is empty when the daemon is renamed with `exec -a`.
PYTHON = sys.executable or "/usr/bin/python3"

# Written by entrypoint.sh only on the dev deployment (docker-compose.dev.yml);
# readable by 'drill' alone. Without it the cheat code does not exist.
DEV_CONFIG = os.environ.get("DCU_DEV_CONFIG", "/etc/dcu/dev.conf")


def load_dev_config():
    """Returns (code, teams). Lines are code=<x> or team=<name>."""
    code, teams = None, set()
    try:
        with open(DEV_CONFIG) as f:
            for line in f:
                key, _, value = line.strip().partition("=")
                if key == "code" and value:
                    code = value.upper()
                elif key == "team" and value:
                    teams.add(value)
    except OSError:
        pass
    return (code, teams) if code and teams else (None, set())


DEV_CODE, DEV_TEAMS = load_dev_config()

competition = None  # set in main() when serving the competitive unit


def peer_team(conn):
    creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", creds)
    return pwd.getpwuid(uid).pw_name


def read_command(conn):
    """Read the one-line command byte by byte so nothing meant for the challenge is consumed."""
    data = b""
    while len(data) < 64:
        ch = conn.recv(1)
        if not ch or ch == b"\n":
            break
        data += ch
    return data.decode(errors="replace").strip().upper()


def progress_file(team, unit):
    return os.path.join(PROGRESS_DIR, team, f"unit{unit}.mined")


def dev_file(team):
    return os.path.join(PROGRESS_DIR, team, "dev.unlocked")


def dev_unlocked(team):
    return team in DEV_TEAMS and os.path.exists(dev_file(team))


def toggle_dev(team):
    if os.path.exists(dev_file(team)):
        os.remove(dev_file(team))
        return f"[DEV] Unlock removed for {team}. Units are locked by progress again."
    os.makedirs(os.path.join(PROGRESS_DIR, team), exist_ok=True)
    open(dev_file(team), "w").close()
    return f"[DEV] All units unlocked for {team}. Enter the code again to re-lock."


def state(team, unit):
    locked = unit > 1 and unit not in UNGATED and not os.path.exists(progress_file(team, unit - 1))
    if locked and not dev_unlocked(team):
        return "LOCKED"
    tag = " (DEV)" if locked else ""
    if competition:
        return competition.status() + tag
    if os.path.exists(progress_file(team, unit)):
        return "MINED"
    return "ONLINE" + tag


def mark_mined(team, unit):
    os.makedirs(os.path.join(PROGRESS_DIR, team), exist_ok=True)
    open(progress_file(team, unit), "w").close()


def handle(conn, unit):
    with conn:
        try:
            team = peer_team(conn)
            command, _, arg = read_command(conn).partition(" ")
            if command == "CODE":
                if DEV_CODE and team in DEV_TEAMS and arg.strip() == DEV_CODE:
                    conn.sendall(f"{toggle_dev(team)}\n".encode())
                return
            current = state(team, unit)
            if command == "STATUS":
                conn.sendall(f"{current}\n".encode())
                return
            if current == "LOCKED":
                if command == "ENTER":
                    conn.sendall(
                        f"[!] ACCESS DENIED. DCU {UNIT_NAMES[unit]} is sealed.\n"
                        f"[!] Mine DCU {UNIT_NAMES[unit - 1]} to restore power to this unit.\n".encode()
                    )
                return
            if competition:
                if command == "SCORE":
                    conn.sendall(f"{competition.score_line(team)}\n".encode())
                elif command == "SCOREBOARD":
                    conn.sendall(competition.scoreboard().encode())
                elif command == "ENTER":
                    competition.session(conn.makefile("rb"), conn.sendall, team)
                return
            if command != "ENTER":
                return
            # argv[0] is what shows up in ps for this session.
            rc = subprocess.call(
                [f"DCU {UNIT_NAMES[unit]} session ({team})", "-u", os.path.join(CODE_DIR, UNITS[unit])],
                executable=PYTHON,
                stdin=conn,
                stdout=conn,
                stderr=subprocess.DEVNULL,
                cwd=CODE_DIR,
                env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
            )
            if rc == 0:
                mark_mined(team, unit)
        except (OSError, KeyError):
            pass


def load_competition():
    sys.dont_write_bytecode = True  # never leave a readable .pyc of the challenge behind
    spec = importlib.util.spec_from_file_location("crypto_level3", os.path.join(CODE_DIR, UNITS[COMPETITIVE_UNIT]))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    return module.Competition(PROGRESS_DIR)


def main():
    global competition
    unit = int(sys.argv[1])
    if unit not in UNITS:
        sys.exit(f"unknown unit {unit}")
    if unit == COMPETITIVE_UNIT:
        competition = load_competition()
    os.makedirs(SOCKET_DIR, exist_ok=True)
    path = os.path.join(SOCKET_DIR, f"unit{unit}.sock")
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(path)
    os.chmod(path, 0o666)  # any team may connect; access is decided per connection
    server.listen()
    while True:
        conn, _ = server.accept()
        threading.Thread(target=handle, args=(conn, unit), daemon=True).start()


if __name__ == "__main__":
    main()
