#!/bin/bash
# scenario.sh -- run ON THE PROXMOX HOST. Replays the First Boot onboarding session on
# VM 404 from the `clean` snapshot, then does a full shutdown so collect.sh can run.
#
# Timeline (one boot, the trainee auto-logs on):
#   baseline : notepad, calc, Explorer from Win+R (ordinary first-day noise in RunMRU/Prefetch)
#   +3 min   : the ONBOARD stick is hot-plugged (USBSTOR / MountedDevices)
#   +1 min   : Win+R  F:\crew_setup.exe  (the helper's step; Prefetch + RunMRU + NTUSER key)
#   +1 min   : stick pulled, a little more noise, then `shutdown /s /t 0` (full, hives flushed)
# The stick lands on F: because the VM keeps two (empty) CD drives on D: and E:.
#
# Usage: scenario.sh <stick.img>   (the built stick: crew_setup.exe + profiles\<HEX>.cal)
set -euo pipefail
VMID=404
STICK=$(realpath "$1")
HERE=$(dirname "$(realpath "$0")")
mon() { printf '%s\n' "$@" | qm monitor $VMID >/dev/null; }
run() { qm sendkey $VMID meta_l-r; sleep 2; "$HERE/vmtype.py" $VMID "$1" --enter; }
close() { sleep "$1"; qm sendkey $VMID alt-f4; }

qm rollback $VMID clean
qm start $VMID
sleep 90                                   # boot + auto-logon + first-desktop settle

run notepad;  close 20
run calc;     close 15
run explorer; close 15
sleep 180

mon "drive_add 0 if=none,id=stick,format=raw,file=$STICK" \
    "device_add usb-storage,id=stick0,drive=stick,bus=ehci.0,port=2"
sleep 60
run 'F:\crew_setup.exe'
sleep 60                                   # tool runs ~7 s; prefetch is written ~10 s after launch

mon "device_del stick0"; sleep 3; mon "drive_del stick" || true
sleep 30
run notepad;  close 20
sleep 60

run 'shutdown /s /t 0'
for _ in $(seq 1 60); do
  [ "$(qm status $VMID | awk '{print $2}')" = stopped ] && { echo "scenario done, VM stopped"; exit 0; }
  sleep 5
done
echo "VM did not stop in time"; exit 1
