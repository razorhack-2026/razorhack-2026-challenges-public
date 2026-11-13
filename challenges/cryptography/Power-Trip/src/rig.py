#!/usr/bin/env python3
"""RazerPowerCo interlock bench rig.

One process per connection (socat forks and hands us a pty), so there is no
shared state between teams. Speaks a line-oriented ASCII protocol on stdin /
stdout. Competitors get no protocol handout: the banner and HELP below are the
only documentation, so keep them accurate.

The rig is two devices on one link, wired the way a real bench is:

  TARGET  the RPC-IC220 board. Takes a request over its UART, runs the
          authentication routine, answers with the ciphertext. It does not know
          a scope exists; it just raises a trigger GPIO around the routine.
  SCOPE   the shunt capture unit. Armed by hand, triggers on that GPIO edge,
          digitises `samples` samples starting `offset` past the trigger, at
          `gain` dB. Capture depth is shorter than the routine, so the operator
          has to decide which part of it to look at.

Per capture:
  1. Unicorn runs the real firmware image (Thumb, Cortex-M0).
  2. Every data-side memory access inside the trigger window contributes one
     analog sample, the Hamming weight of the value on the bus.
  3. Analog noise is added, then the scope windows and digitises it.

The noise is derived from HMAC(device_key, plaintext), so one plaintext always
produces the same analog signal -- windowing and gain are just different views
of it. That stops the trivial attack of averaging thousands of captures of a
single plaintext to erase the noise, and makes a dropped link resumable.
"""
import base64
import hashlib
import hmac
import os
import pathlib
import sys

import numpy as np
from unicorn import (
    Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_PROT_ALL,
    UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_WRITE, UcError,
)
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_SP

# ------------------------------------------------------- analog front end
# Noise lives on the analog side, ahead of the amplifier, so gain scales signal
# and noise together and cannot improve SNR. What gain decides is only how much
# of the ADC's range gets used.
#
# Measured, so nobody has to guess: the usable gain range is very wide. CPA
# still recovers the key at +40dB with 93% of samples clipped, because the
# attack uses whatever samples stay linear. It fails only at or below -36dB,
# where the whole trace collapses into 3 codes and the signal is gone. So gain
# is a real setup step -- the scope powers up below that floor -- but it is not
# the difficulty. The window is.
#
# Calibrated against this firmware, at a sane gain and a window covering the
# first round: 16/16 bytes at 4000 traces, 15/16 at 3000, 12/16 at 2000.
# ANALOG_NOISE is the difficulty dial; re-run the sweep if it or the firmware
# changes.
ANALOG_NOISE = 18.0
IDLE_NOISE_RATIO = 0.25   # the rail is quieter outside the trigger window
TRIGGER_AMPLITUDE = 55.0  # the GPIO toggle, in analog units

# The board toggles its trigger GPIO at the start of the routine; on the shunt
# that reads as this fixed burst.
TRIGGER = np.array([1.0, -1.0, .92, -.96, 1.0, -.92, .96, -1.0, .94, -1.0,
                    1.0, -.94]) * TRIGGER_AMPLITUDE

# ------------------------------------------------------- scope limits
# The authentication routine is ~3960 samples long and capture depth is 1024,
# so no single capture covers all of it. Choosing the window is the operator's
# job, exactly as it is with a real scope's memory depth.
MAX_SAMPLES = 1024
DEFAULT_SAMPLES = 256
MAX_OFFSET = 8192
DEFAULT_OFFSET = 0
GAIN_MIN_DB = -40.0
GAIN_MAX_DB = 40.0
DEFAULT_GAIN_DB = -40.0    # below the usable floor; the operator must tune it

ANALOG_LEN = MAX_OFFSET + MAX_SAMPLES

# ------------------------------------------------------- memory map
FLASH_BASE = 0x08000000
FLASH_SIZE = 64 * 1024
SRAM_BASE = 0x20000000
SRAM_SIZE = 8 * 1024
IO_BASE = 0x30000000          # rig IO block; deliberately outside SRAM
IO_SIZE = 0x1000
MMIO_BASE = 0x40000000
MMIO_SIZE = 0x1000
TRIG_ADDR = 0x40000000

IO_KEY = IO_BASE + 0x00
IO_PT = IO_BASE + 0x10
IO_CT = IO_BASE + 0x20

MAX_CAPTURES = 50_000
MAX_BATCH = 500
INSN_LIMIT = 4_000_000

POPCOUNT = bytes(bin(i).count("1") for i in range(256))


def _popcount(value: int, size: int) -> int:
    total = 0
    for _ in range(size):
        total += POPCOUNT[value & 0xFF]
        value >>= 8
    return total


class Target:
    """The emulated RPC-IC220."""

    def __init__(self, firmware: bytes, device_key: bytes):
        self.device_key = device_key
        self.events: list[float] = []
        self.armed = False

        uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, FLASH_SIZE, UC_PROT_ALL)
        uc.mem_map(SRAM_BASE, SRAM_SIZE, UC_PROT_ALL)
        uc.mem_map(IO_BASE, IO_SIZE, UC_PROT_ALL)
        uc.mem_map(MMIO_BASE, MMIO_SIZE, UC_PROT_ALL)
        uc.mem_write(FLASH_BASE, firmware)

        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self._on_mem)
        self.uc = uc

    def _on_mem(self, uc, access, address, size, value, user_data):
        if address == TRIG_ADDR:
            if access == UC_MEM_WRITE:
                if value:
                    self.armed = True
                else:
                    self.armed = False
                    uc.emu_stop()
            return
        if not self.armed:
            return

        if access == UC_MEM_WRITE:
            bus = value
        else:
            # UC_HOOK_MEM_READ_AFTER is not wired up in the Python bindings, so
            # the read value never reaches the callback. The read hook fires
            # before the access and cannot change what is there, so reading the
            # location ourselves yields exactly the value about to go on
            # the bus.
            bus = int.from_bytes(uc.mem_read(address, size), "little")

        # Centre each access on its expected weight so idle and active
        # stretches share a baseline.
        self.events.append(_popcount(bus, size) - 4.0 * size)

    def run(self, pt: bytes) -> tuple[bytes, np.ndarray]:
        """Run one authentication request; return ciphertext and leakage."""
        uc = self.uc
        uc.mem_write(SRAM_BASE, b"\x00" * SRAM_SIZE)
        uc.mem_write(IO_BASE, b"\x00" * 0x40)
        uc.mem_write(MMIO_BASE, b"\x00" * 4)
        uc.mem_write(IO_KEY, self.device_key)
        uc.mem_write(IO_PT, pt)

        self.events = []
        self.armed = False
        uc.reg_write(UC_ARM_REG_SP, SRAM_BASE + SRAM_SIZE)
        uc.reg_write(UC_ARM_REG_PC, FLASH_BASE | 1)
        try:
            uc.emu_start(FLASH_BASE | 1, 0, 0, INSN_LIMIT)
        except UcError:
            # emu_stop() from the trigger hook unwinds through here on some
            # builds; the ciphertext is already in place either way.
            pass

        ct = bytes(uc.mem_read(IO_CT, 16))
        return ct, np.asarray(self.events, dtype=np.float64)

    def analog(self, pt: bytes) -> tuple[bytes, np.ndarray]:
        """The shunt waveform for one request, before the scope sees it."""
        ct, leakage = self.run(pt)

        seed = hmac.new(self.device_key, pt, hashlib.sha256).digest()
        rng = np.random.default_rng(int.from_bytes(seed[:8], "big"))

        live = np.concatenate([TRIGGER, leakage])
        wave = np.full(ANALOG_LEN, -4.0)
        end = min(ANALOG_LEN, live.size)
        wave[:end] = live[:end]

        scale = np.full(ANALOG_LEN, ANALOG_NOISE * IDLE_NOISE_RATIO)
        scale[:end] = ANALOG_NOISE
        return ct, wave + rng.normal(0.0, 1.0, ANALOG_LEN) * scale


class Scope:
    """The shunt capture unit: depth, delay, gain, arm, read."""

    def __init__(self):
        self.samples = DEFAULT_SAMPLES
        self.offset = DEFAULT_OFFSET
        self.gain_db = DEFAULT_GAIN_DB
        self.armed = False
        self.buffer = None

    def describe(self) -> str:
        return (f"SCOPE samples={self.samples} offset={self.offset} "
                f"gain={self.gain_db:g}dB depth_max={MAX_SAMPLES} "
                f"armed={'yes' if self.armed else 'no'} "
                f"buffer={'ready' if self.buffer is not None else 'empty'}")

    def digitise(self, wave: np.ndarray) -> bytes:
        """Window the analog trace, apply gain, quantise to signed 8-bit."""
        window = wave[self.offset:self.offset + self.samples]
        gain = 10.0 ** (self.gain_db / 20.0)
        counts = np.rint(window * gain)
        return np.clip(counts, -128, 127).astype(np.int8).tobytes()


# ---------------------------------------------------------------- protocol

# The rig documents itself. Competitors are given only the sealed record, so
# everything needed to drive the link has to be reachable in-band -- which is
# also how a real instrument behaves.
BANNER = """\
RazerPowerCo field bench rig -- two devices on one link
TARGET  : RPC-IC220 interlock controller (Cortex-M0), UART request/response
SCOPE   : shunt capture unit, 20 mOhm, signed 8-bit, max depth {d} samples
NOTE    : the target's routine is longer than the scope can hold in one capture
NOTE    : the scope powers up at {g:g}dB / {s} samples / offset {o} -- unusable
NOTE    : captures are repeatable -- one request, one waveform, every time
Type HELP for commands.""".format(d=MAX_SAMPLES, g=DEFAULT_GAIN_DB,
                                  s=DEFAULT_SAMPLES, o=DEFAULT_OFFSET)

HELP = """\
ID                     report target identification
SCOPE                  report capture settings
SCOPE SET SAMPLES <n>  capture depth, 1..{d}
SCOPE SET OFFSET <n>   samples to skip after the trigger, 0..{o}
SCOPE SET GAIN <db>    amplifier gain, {lo:g}..{hi:g} dB
SCOPE ARM              arm on the next trigger edge
SCOPE READ             read the captured waveform  -> WAVE <base64>
TARGET SEND <32 hex>   run one request        -> TARGET <plaintext> <cipher>
BATCH <n>              n armed requests at the current settings (max {b})
STATUS                 captures used / remaining on this session
QUIT                   close the link

Single capture is three steps: SCOPE ARM, TARGET SEND, SCOPE READ. The target
runs whether or not the scope is armed; an unarmed request leaves the buffer
untouched. BATCH lines are: CAP <plaintext> <ciphertext> <base64 waveform>.
Waveforms decode to `samples` signed 8-bit values of shunt current.
Session budget is {c} requests; reconnecting resets it.""".format(
    d=MAX_SAMPLES, o=MAX_OFFSET, lo=GAIN_MIN_DB, hi=GAIN_MAX_DB,
    b=MAX_BATCH, c=MAX_CAPTURES)


def load_device_key() -> bytes:
    env = os.environ.get("DEVICE_KEY")
    if env:
        return bytes.fromhex(env.strip())
    path = pathlib.Path(__file__).resolve().parent / "device_key.txt"
    return bytes.fromhex(path.read_text().strip())


def load_firmware() -> bytes:
    env = os.environ.get("RIG_FIRMWARE")
    if env:
        return pathlib.Path(env).read_bytes()
    here = pathlib.Path(__file__).resolve().parent
    return (here / "firmware" / "target.bin").read_bytes()


def _scope_set(scope: Scope, args: list[str]) -> str:
    if len(args) != 2:
        return "ERR usage: SCOPE SET <SAMPLES|OFFSET|GAIN> <value>"
    field, raw = args[0].upper(), args[1]
    try:
        value = float(raw)
    except ValueError:
        return f"ERR {field.lower()} must be numeric"

    if field == "SAMPLES":
        if not 1 <= value <= MAX_SAMPLES:
            return f"ERR samples out of range, 1..{MAX_SAMPLES}"
        scope.samples = int(value)
    elif field == "OFFSET":
        if not 0 <= value <= MAX_OFFSET:
            return f"ERR offset out of range, 0..{MAX_OFFSET}"
        scope.offset = int(value)
    elif field == "GAIN":
        if not GAIN_MIN_DB <= value <= GAIN_MAX_DB:
            return (f"ERR gain out of range, "
                    f"{GAIN_MIN_DB:g}..{GAIN_MAX_DB:g} dB")
        scope.gain_db = value
    else:
        return "ERR settable: SAMPLES, OFFSET, GAIN"
    return "OK " + scope.describe()


def serve(target: Target, fin, fout) -> int:
    """Run the protocol loop over one already-open link."""
    def out(line: str) -> None:
        fout.write(line + "\r\n")
        fout.flush()

    scope = Scope()
    used = 0

    out(BANNER)
    for raw in fin:
        parts = raw.strip().split()
        if not parts:
            continue
        cmd, args = parts[0].upper(), parts[1:]

        if cmd == "QUIT":
            out("BYE")
            return 0
        if cmd == "HELP":
            out(HELP)
            continue
        if cmd == "ID":
            out("ID RPC-IC220 rev C  fw 2.4.1  interlock-auth AES-128")
            continue
        if cmd == "STATUS":
            out(f"OK used={used} remaining={MAX_CAPTURES - used}")
            continue

        if cmd == "SCOPE":
            if not args:
                out(scope.describe())
            elif args[0].upper() == "SET":
                out(_scope_set(scope, args[1:]))
            elif args[0].upper() == "ARM":
                scope.armed = True
                out("OK armed")
            elif args[0].upper() == "READ":
                if scope.buffer is None:
                    out("ERR no capture in buffer -- arm the scope, then send "
                        "a request")
                else:
                    out(f"WAVE {base64.b64encode(scope.buffer).decode()}")
            else:
                out("ERR SCOPE takes SET, ARM or READ")
            continue

        if cmd == "TARGET":
            if len(args) != 2 or args[0].upper() != "SEND":
                out("ERR usage: TARGET SEND <32 hex>")
                continue
            if used >= MAX_CAPTURES:
                out("ERR request budget exhausted for this session, reconnect")
                continue
            try:
                pt = bytes.fromhex(args[1])
            except ValueError:
                out("ERR plaintext must be hex")
                continue
            if len(pt) != 16:
                out("ERR plaintext must be 16 bytes")
                continue

            ct, wave = target.analog(pt)
            used += 1
            if scope.armed:
                scope.buffer = scope.digitise(wave)
                scope.armed = False
            out(f"TARGET {pt.hex()} {ct.hex()}")
            continue

        if cmd == "BATCH":
            if not args or not args[0].isdigit():
                out("ERR usage: BATCH <n>")
                continue
            n = min(int(args[0]), MAX_BATCH, MAX_CAPTURES - used)
            if n <= 0:
                out("ERR request budget exhausted for this session, reconnect")
                continue
            # BATCH arms itself for each request, the way a scripted capture
            # loop does. The last waveform stays in the buffer so a following
            # SCOPE READ behaves the same as it would after a single shot.
            for _ in range(n):
                pt = os.urandom(16)
                ct, wave = target.analog(pt)
                used += 1
                scope.buffer = scope.digitise(wave)
                out(f"CAP {pt.hex()} {ct.hex()} "
                    f"{base64.b64encode(scope.buffer).decode()}")
            scope.armed = False
            out(f"END {n}")
            continue

        out("ERR unknown command, try HELP")

    return 0


def main() -> int:
    target = Target(load_firmware(), load_device_key())
    return serve(target, sys.stdin, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
