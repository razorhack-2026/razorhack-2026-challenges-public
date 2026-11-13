#!/bin/bash
# collect.sh -- run ON THE PROXMOX HOST after the scenario, with VM 404 shut down
# (a full `shutdown /s`, not a hybrid/fast-startup one, so the hives are flushed).
# Maps the VM disk read-only, mounts the Windows partition read-only (ntfs3) and
# copies the artifact set in a KAPE-like tree, transaction logs included so the
# EZ tools can replay any dirty hive. Nothing on the VM disk is modified.
# ntfs3 is case-sensitive: the on-disk dir is Windows\appcompat, not AppCompat.
#
# Usage: collect.sh <out_dir>   -> <out_dir>/first-boot-artifacts.zip
set -euo pipefail
VMID=404
USER_NAME=trainee
OUT=$(realpath "$1")

[ "$(qm status $VMID | awk '{print $2}')" = stopped ] || { echo "VM $VMID must be stopped"; exit 1; }
LV=$(qm config $VMID | sed -n 's/^sata0: local-lvm:\([^,]*\),.*/\/dev\/pve\/\1/p')
lvchange -ay "$LV" >/dev/null 2>&1 || true

LOOP=$(losetup -f --show -r -P "$LV")
MNT=$(mktemp -d); DIS=
cleanup() {
  umount "$MNT" 2>/dev/null || true
  [ -n "$DIS" ] && { umount "$DIS" 2>/dev/null || true; rmdir "$DIS"; }
  losetup -d "$LOOP"; rmdir "$MNT"
}
trap cleanup EXIT
WINPART="${LOOP}p3"
if blkid -o value -s TYPE "$WINPART" | grep -q BitLocker; then
  # Win11 turns on device encryption by itself (vTPM present). With no Microsoft
  # account to escrow the key it keeps a clear-key protector, which dislocker
  # opens offline (apt install dislocker on the host).
  DIS=$(mktemp -d)
  dislocker-fuse -r -c -V "$WINPART" -- "$DIS"
  mount -t ntfs3 -o ro,loop "$DIS/dislocker-file" "$MNT"
else
  mount -t ntfs3 -o ro "$WINPART" "$MNT"
fi

STAGE=$(mktemp -d)/first-boot-artifacts
mkdir -p "$STAGE"/C/Windows/{Prefetch,System32/config,AppCompat/Programs} "$STAGE/C/Users/$USER_NAME"
cp -p "$MNT"/Windows/Prefetch/*.pf "$STAGE"/C/Windows/Prefetch/
# Drop any .pf without the Win10+ MAM header: the 2026-11-04 run read one baseline
# file (CTFMON.EXE) as noise through dislocker. Shipping it would read as a planted
# red herring, so it is left out and logged here.
for pf in "$STAGE"/C/Windows/Prefetch/*.pf; do
  [ "$(head -c 3 "$pf")" = MAM ] || { echo "dropped unreadable prefetch: $(basename "$pf")" >&2; rm "$pf"; }
done
for h in SYSTEM SOFTWARE; do
  cp -p "$MNT"/Windows/System32/config/$h{,.LOG1,.LOG2} "$STAGE"/C/Windows/System32/config/ 2>/dev/null || \
  cp -p "$MNT"/Windows/System32/config/$h "$STAGE"/C/Windows/System32/config/
done
cp -p "$MNT"/Windows/appcompat/Programs/Amcache.hve* "$STAGE"/C/Windows/AppCompat/Programs/
UH=$(ls -d "$MNT"/Users/* | grep -i "/$USER_NAME" | head -1)
cp -p "$UH"/NTUSER.DAT "$UH"/ntuser.dat.LOG1 "$UH"/ntuser.dat.LOG2 "$STAGE/C/Users/$USER_NAME/" 2>/dev/null || \
cp -p "$UH"/NTUSER.DAT "$STAGE/C/Users/$USER_NAME/"

mkdir -p "$OUT"; rm -f "$OUT/first-boot-artifacts.zip"
(cd "$(dirname "$STAGE")" && python3 - "$OUT/first-boot-artifacts.zip" <<'EOF'
import os, sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as z:
    for d, _, fs in sorted(os.walk("first-boot-artifacts")):
        for f in sorted(fs):
            z.write(os.path.join(d, f))
EOF
)
find "$STAGE" -type f | sed "s|$STAGE/||" | sort
ls -la "$OUT/first-boot-artifacts.zip"
rm -rf "$(dirname "$STAGE")"
