#!/bin/bash
# Creates the team accounts, starts the DCU daemons as 'drill', then runs sshd.
#   DCU_UNITS           the units this server runs (default "1 2 3"). Per-team copies
#                       run "1 2"; the shared Mole-03 server runs "3".
#   DCU_UNGATED         units open without the one before them mined (dcu_daemon.py).
#   DCU_RESET_AND_EXIT  1: empty the saved progress, then stop (the admin Reset).
set -e

PROGRESS_DIR="${DCU_PROGRESS_DIR:-/var/lib/dcu}"
if [ "${DCU_RESET_AND_EXIT:-}" = "1" ]; then
    [ ! -d "$PROGRESS_DIR" ] || find "$PROGRESS_DIR" -mindepth 1 -delete
    echo "DCU RESET: saved progress in $PROGRESS_DIR removed"
    exit 0
fi

UNITS="${DCU_UNITS:-1 2 3}"
for unit in $UNITS; do
    case "$unit" in
        1 | 2 | 3) ;;
        *) echo "DCU_UNITS: no unit $unit" >&2; exit 1 ;;
    esac
done
# The console reads which units this server runs from here (teams' SSH sessions don't
# see the container's environment). Nothing in it is secret.
printf 'units=%s\n' "$UNITS" > /etc/dcu/units.conf
chmod 644 /etc/dcu/units.conf
# A volume mounted over the progress dir (EFS on the shared server) starts root-owned.
install -d -o drill -g drill -m 700 "$PROGRESS_DIR"

# Team files have user:password lines; blank lines and lines starting with '#' are skipped.
team_lines() {
    grep -v -e '^[[:space:]]*$' -e '^#' "$1" || true
}

add_teams() {
    team_lines "$1" | while IFS= read -r line; do
        team="${line%%:*}"
        if ! id "$team" >/dev/null 2>&1; then
            # '#' and capitals aren't "standard" usernames; Debian allows them, --badname is the fallback.
            useradd --create-home --shell /bin/bash --groups teams "$team" 2>/dev/null \
                || useradd --badname --create-home --shell /bin/bash --groups teams "$team"
            chmod 700 "/home/$team"
        fi
        echo "$line" | chpasswd
    done
}

add_teams /etc/dcu/teams.txt

# Per-team copy (Fargate): only one team can reach this server, so every team account gets
# the one password its connection info gives. Unset (compose), teams.txt's passwords stand.
if [ -n "${TEAM_PASSWORD:-}" ]; then
    team_lines /etc/dcu/teams.txt | cut -d: -f1 | while IFS= read -r team; do
        printf '%s:%s\n' "$team" "$TEAM_PASSWORD"
    done | chpasswd
fi

# Dev deployment only: docker-compose.dev.yml mounts THE-DRILL/dev at /root/dev
# (unreadable to teams). Its accounts get the cheat code; production has neither.
rm -f /etc/dcu/dev.conf
if [ -f /root/dev/teams.txt ] && [ -s /root/dev/code.txt ]; then
    add_teams /root/dev/teams.txt
    {
        echo "code=$(head -n 1 /root/dev/code.txt | tr -d '[:space:]')"
        team_lines /root/dev/teams.txt | cut -d: -f1 | sed 's/^/team=/'
    } > /etc/dcu/dev.conf
    chown drill:drill /etc/dcu/dev.conf
    chmod 600 /etc/dcu/dev.conf
    echo "DEV DEPLOYMENT: dev accounts and cheat code enabled"
fi

install -d -o drill -g drill -m 755 /run/dcu
mkdir -p /run/sshd
# Host keys live in a bind mount so teams don't get "host identification changed" after a rebuild.
for type in ed25519 ecdsa rsa; do
    key="/etc/ssh/host_keys/ssh_host_${type}_key"
    [ -f "$key" ] || ssh-keygen -q -t "$type" -N '' -f "$key"
done

unit_names=("" Termite-01 Dog-02 Mole-03)
unit_files=("" crypto.py crypto_level2.py crypto_level3.py)
for unit in $UNITS; do
    # A unit whose file isn't in the image yet shows as OFFLINE in the console.
    [ -f "/opt/dcu/${unit_files[$unit]}" ] || continue
    # Restart a unit if it ever dies. exec -a sets the name shown in ps.
    (while true; do
        setpriv --reuid=drill --regid=drill --init-groups \
            bash -c 'exec -a "DRILL CONTAINMENT UNIT $2" python3 /opt/dcu/dcu_daemon.py "$1"' _ "$unit" "${unit_names[$unit]}"
        sleep 1
    done) &
done

exec /usr/sbin/sshd -D -e
