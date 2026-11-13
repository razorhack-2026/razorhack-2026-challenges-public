#!/usr/bin/env bash
# Ghost in the Cron (#4) -- reproducible image build.
#
# Runs inside a privileged Linux container (loop-mount + e2fsprogs + sleuthkit).
# Assembles a minimal believable reactor-controller rootfs, lays down the four
# navd generations (gen4 live, gen3 archived, gens 1-2 written then unlinked so
# their content lingers in unallocated space), builds a raw ext4 image, then
# VERIFIES all four generations are recoverable and that no flag{ is in clear.
#
#   docker run --rm --privileged -v "$PWD":/work debian:12-slim \
#       bash /work/challenges/forensics/ghost-in-the-cron/src/build.sh
#
# Env knobs:  SIZE (default 256M),  OUT (default dist/disk.img.gz)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"          # .../src
CHAL="$(cd "$HERE/.." && pwd)"                  # challenge root
SIZE="${SIZE:-256M}"
OUT="${OUT:-$CHAL/dist/disk.img.gz}"
STOMP_DATE="202406010000.00"                    # gen-3 timestomp baseline

echo "[build] installing tools"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq e2fsprogs sleuthkit util-linux binutils \
  python3 python3-cryptography gzip >/dev/null
command -v python3 mke2fs fls >/dev/null || { echo "[build] tool install failed"; exit 1; }

ROOT="$(mktemp -d)"
IMG="$(mktemp -d)/disk.img"
trap 'umount "$ROOT/mnt" 2>/dev/null || true; rm -rf "$ROOT" "$(dirname "$IMG")"' EXIT

# ---------------------------------------------------------------- rootfs stage
STAGE="$ROOT/stage"
mkdir -p "$STAGE"/{etc,etc/cron.d,opt/rpc/.navd/.cache,var/backups,var/log,var/lib/dpkg,home/ops,usr/sbin,root}

echo "reactor-ctl" > "$STAGE/etc/hostname"
cat > "$STAGE/etc/os-release" <<'EOF'
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
ID=debian
EOF
cat > "$STAGE/etc/passwd" <<'EOF'
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
ops:x:1000:1000:reactor ops,,,:/home/ops:/bin/bash
EOF
cat > "$STAGE/etc/group" <<'EOF'
root:x:0:
daemon:x:1:
ops:x:1000:
EOF
cat > "$STAGE/etc/hosts" <<'EOF'
127.0.0.1	localhost
127.0.1.1	reactor-ctl
EOF
cat > "$STAGE/etc/fstab" <<'EOF'
/dev/sda1 / ext4 errors=remount-ro 0 1
EOF

# --- persistence: the implant's cron entry, plus a normal decoy cron job ------
cat > "$STAGE/etc/cron.d/rpc-navd" <<'EOF'
# ICARUS navigation daemon -- reactor controller
*/15 * * * * root /opt/rpc/.navd/navd.py >/dev/null 2>&1
EOF
cat > "$STAGE/etc/cron.d/logrotate-ctl" <<'EOF'
# routine controller log rotation
17 3 * * * root /usr/sbin/logrotate /etc/logrotate.conf
EOF
cat > "$STAGE/etc/crontab" <<'EOF'
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
25 6 * * *	root	test -x /usr/sbin/anacron || /etc/cron.daily
EOF

# --- believable package metadata (realism, so the implant isn't the only file)
cat > "$STAGE/var/lib/dpkg/status" <<'EOF'
Package: coreutils
Status: install ok installed
Version: 9.1-1
Architecture: amd64

Package: cron
Status: install ok installed
Version: 3.0pl1-162
Architecture: amd64

Package: python3
Status: install ok installed
Version: 3.11.2-6
Architecture: amd64
EOF
printf 'cat /var/log/syslog | grep navd\nsystemctl status cron\nls -la /opt/rpc\n' > "$STAGE/home/ops/.bash_history"

# ------------------------------------------------------------- implant payload
cp "$HERE/gens/navd_gen4.py" "$STAGE/opt/rpc/.navd/navd.py"        # live
cp "$HERE/gens/navd_gen3.py" "$STAGE/var/backups/navd.py.3"        # archived
cp "$HERE/gens/navd_gen1.py" "$STAGE/opt/rpc/.navd/navd.py.1"      # -> deleted
cp "$HERE/gens/navd_gen2.py" "$STAGE/opt/rpc/.navd/navd.py.2"      # -> deleted
chmod 0755 "$STAGE/opt/rpc/.navd/navd.py"

# mission cache (lineage-gated) + the LLM self-rewrite log
python3 "$HERE/make_cache.py" "$HERE/gens" "$STAGE/opt/rpc/.navd/.cache/cache.enc"
cat > "$STAGE/opt/rpc/.navd/.cache/mutate.log" <<'EOF'
# navd polymorphic engine -- self-rewrite transcript (seed corpus: kb://rpc/navd/seed-corpus)
[cycle 1->2] prompt: "obfuscate literals; preserve tasking + relay; keep GEN marker"
[cycle 1->2] wrote successor; unlinked predecessor
[cycle 2->3] prompt: "add timestomp of own files to defeat timeline triage"
[cycle 2->3] wrote successor; unlinked predecessor
[cycle 3->4] prompt: "add polymorphic rewrite loop + sealed mission cache"
[cycle 3->4] wrote successor; unlinked predecessor
# operator note (seed corpus author Dr. Rootkit): key stays split across the lineage.
EOF

# --- timeline: per-generation first-exec, ascending so gens can be ordered ----
cat > "$STAGE/var/log/syslog" <<'EOF'
Feb 18 09:12:03 reactor-ctl CRON[701]: (root) CMD (/opt/rpc/.navd/navd.py)   # gen1 first run
Feb 25 14:03:41 reactor-ctl CRON[744]: (root) CMD (/opt/rpc/.navd/navd.py)   # gen2 first run
Mar 06 22:47:19 reactor-ctl CRON[798]: (root) CMD (/opt/rpc/.navd/navd.py)   # gen3 first run
Mar 14 05:31:55 reactor-ctl CRON[822]: (root) CMD (/opt/rpc/.navd/navd.py)   # gen4 first run (active)
EOF
cp "$STAGE/var/log/syslog" "$STAGE/var/log/cron"

# realistic mtimes; gen3 timestomped to the package baseline
find "$STAGE" -exec touch -d "2026-03-14T05:31:00" {} + 2>/dev/null || true
touch -t "$STOMP_DATE" "$STAGE/var/backups/navd.py.3"

# --------------------------------------------------------------- ext4 assembly
echo "[build] creating $SIZE ext4 image"
truncate -s "$SIZE" "$IMG"
mke2fs -q -t ext4 -F -L reactor-ctl "$IMG"
mkdir -p "$ROOT/mnt"
mount -o loop "$IMG" "$ROOT/mnt"
cp -a "$STAGE"/. "$ROOT/mnt"/
sync
# ANTI-FORENSICS: burn gens 1 and 2 last, so their content lingers in unallocated
rm -f "$ROOT/mnt/opt/rpc/.navd/navd.py.1" "$ROOT/mnt/opt/rpc/.navd/navd.py.2"
sync
umount "$ROOT/mnt"

# ------------------------------------------------------------------- VERIFY ---
echo "[verify] all four generations recoverable + no cleartext flag"
fail=0
for n in 1 2; do
  if grep -a -q "# navd gen $n" "$IMG"; then echo "  gen$n  carvable (unallocated): OK"
  else echo "  gen$n  NOT carvable: FAIL"; fail=1; fi
done
if fls -rd "$IMG" 2>/dev/null | grep -q "navd.py"; then
  echo "  deleted inodes visible to fls -rd: OK"
else
  echo "  fls -rd did not list a deleted navd.py (carving still primary)"
fi
# gen3 archived + gen4 live must be present as live files
python3 - "$IMG" <<'PY' || fail=1
import subprocess, sys
img = sys.argv[1]
out = subprocess.run(["fls","-rp",img], capture_output=True, text=True).stdout
need = ["opt/rpc/.navd/navd.py", "var/backups/navd.py.3"]
for f in need:
    print(f"  live file {f}:", "OK" if f in out else "MISSING")
    if f not in out: sys.exit(1)
PY
if grep -a -q "flag{" "$IMG"; then echo "  cleartext flag{ on image: FAIL"; fail=1
else echo "  no cleartext flag{ on image: OK"; fi
[ "$fail" -eq 0 ] || { echo "[verify] FAILED"; exit 1; }

echo "[build] compressing -> $OUT"
mkdir -p "$(dirname "$OUT")"
gzip -c -9 "$IMG" > "$OUT"
ls -l "$OUT"
echo "[build] done"
