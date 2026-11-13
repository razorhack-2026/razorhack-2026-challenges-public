#!/usr/bin/env python3
"""
IED-PROT-03 -- protection relay GOOSE publisher.

Publishes the trip control block (`gcbTrip`) for the whole maintenance test
window: mostly stable "no trip" heartbeats, a couple of rehearsed trip
toggles (still flagged `test=True`, so a compliant subscriber must ignore
them), and exactly one real event where `test=False` slips out -- the frame
this challenge is about.

Destination is Ethernet broadcast rather than a real GOOSE multicast MAC.
Wireshark's GOOSE dissector doesn't care about the destination address (it
keys off EtherType 0x88b8), and broadcast sidesteps any multicast-snooping
quirks on the Docker bridge -- see solution/solution.md.

MODE controls whether the one genuine (test=False) frame ever actually goes
out:
  - MODE=capture -- runs the full scripted test window once, INCLUDING the
    genuine frame, then exits. Used only offline, by the GM, to generate
    dist/substation_test_window.pcap (see src/capture/). Never run this
    against the live challenge deployment.
  - MODE=live (default) -- the mode contestants actually connect to. Loops
    heartbeats and test=True rehearsal decoys forever, but the real trip
    frame is never sent live -- the incident already happened and was
    captured; the only way to see it fire *now* is to find that exact frame
    in the pcap and replay it onto the wire yourself.
"""

import os
import socket
import struct
import sys
import time

sys.path.insert(0, "/app/common")
import goose  # noqa: E402

IFACE = os.environ.get("IFACE", "eth0")
BROADCAST = b"\xff\xff\xff\xff\xff\xff"
ETHERTYPE_GOOSE = goose.ETHERTYPE_GOOSE

GOCB_REF = "IED_PROT03LLN0$GO$gcbTrip"
DATSET = "IED_PROT03LLN0$TripDataSet"
GO_ID = "gcbTrip"
APPID = 0x0001


def get_mac(iface):
    with open(f"/sys/class/net/{iface}/address") as f:
        return bytes.fromhex(f.read().strip().replace(":", ""))


def open_tx_socket(iface):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETHERTYPE_GOOSE))
    s.bind((iface, ETHERTYPE_GOOSE))
    return s


def send(sock, src_mac, st_num, sq_num, test, trip):
    pdu = goose.build_goose_apdu(
        gocb_ref=GOCB_REF,
        dat_set=DATSET,
        go_id=GO_ID,
        st_num=st_num,
        sq_num=sq_num,
        test=test,
        data_values=[trip],
        conf_rev=1,
    )
    frame = goose.build_goose_frame(BROADCAST, src_mac, APPID, pdu)
    sock.send(frame)
    print(f"[prot] stNum={st_num} sqNum={sq_num} test={test} trip={trip}", flush=True)


def burst(sock, src_mac, st_num, test, trip, count=4, interval=0.3):
    for sq in range(count):
        send(sock, src_mac, st_num, sq, test, trip)
        time.sleep(interval)


def run_schedule(sock, src_mac, schedule, allow_genuine, st_num=1, sq_num=0):
    next_heartbeat = time.time() + 3

    for delay, action in schedule:
        deadline = time.time() + delay
        while time.time() < deadline:
            if time.time() >= next_heartbeat:
                sq_num += 1
                send(sock, src_mac, st_num, sq_num, True, False)
                next_heartbeat = time.time() + 3
            time.sleep(0.1)

        if action == "rehearsal":
            st_num += 1
            burst(sock, src_mac, st_num, True, True)     # trip on, still test
            time.sleep(1.5)
            st_num += 1
            sq_num = 0
            burst(sock, src_mac, st_num, True, False)    # trip off, back to normal
            sq_num = 0
        elif action == "genuine":
            st_num += 1
            if allow_genuine:
                print("[prot] *** sending the real one (test=False) ***", flush=True)
                send(sock, src_mac, st_num, 0, False, True)
            else:
                print("[prot] (live mode: skipping the genuine frame -- "
                      "it only exists in the captured pcap now)", flush=True)
            sq_num = 0
            # Deliberately NOT retransmitted in capture mode -- see
            # solution.md for why a real relay's burst got cut short here.
        elif action == "heartbeat":
            pass

        next_heartbeat = time.time() + 3

    return st_num, sq_num


def main():
    mode = os.environ.get("MODE", "live")
    src_mac = get_mac(IFACE)
    sock = open_tx_socket(IFACE)

    print(f"[prot] starting stable heartbeat (test=True, trip=False) -- MODE={mode}", flush=True)

    # Scripted maintenance test window. Each entry is (delay_before, action).
    # "rehearsal" = a test=True toggle a real crew would run through on
    # purpose during a breaker exercise. "genuine" = the one frame that
    # slipped out for real -- only actually sent when MODE=capture.
    schedule = [
        (20, "rehearsal"),
        (30, "heartbeat"),
        (15, "rehearsal"),
        (15, "genuine"),
        (30, "heartbeat"),
    ]

    st_num, sq_num = run_schedule(sock, src_mac, schedule, allow_genuine=(mode == "capture"))

    if mode == "capture":
        print("[prot] capture window complete, exiting", flush=True)
        return

    print("[prot] test window complete, resuming steady heartbeat + rehearsal decoys", flush=True)
    rehearsal_schedule = [(45, "rehearsal")]
    while True:
        st_num, sq_num = run_schedule(sock, src_mac, rehearsal_schedule, allow_genuine=False,
                                       st_num=st_num, sq_num=sq_num)


if __name__ == "__main__":
    main()
