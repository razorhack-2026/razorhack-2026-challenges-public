# Wi-Fi Challenges
Lt. Rico Kopernicus's Wi-Fi Emporium

## Contents
- `solution/` - All WiFi challenge write-ups
- `build/` - Dockerfiles
- `config/` - AP/Client/Device configs
- `content/` - Files copied onto containers
- `scripts/` - Local helper scripts
- `ctf` - Run `./ctf install` once per VM, then `./ctf start` to spin up the challenges
- `start-wifi-ctf.service` - Linux service file for running on startup (optional)

### [Old Tutorial Video Playlist](https://youtube.com/playlist?list=PLg9_UX_yRKYP2Gl6jqNvoilD9sGgaXUoA&si=hdM9t9FG1HxGGXDb)

## Setup / Deployment Notes

- Each team needs a VM with this setup, can be super lightweight (0.5-1 cpu, 2gb memory, 15-20gb storage, Debian/Kali preferred, Ubuntu should work but untested)
    - Key feature required: The distro used needs to be able to load and unload kernel modules, specifically the `mac80211_hwsim` module.  Without this module, it can't simulate wireless devices and traffic.  See `ctf` for the commands used.
- Clone `challenges/wifi/` using any method
- Install required packages on VM: run `./ctf install`
    - Handles apt / dnf / pacman / zypper / apk, installs Docker Engine + Compose v2 (no Docker Desktop),
      and finishes with a check that lists anything it could not install for your distro.
- Modify port-forwarding for the player's container as needed in `ctf` `cmd_start()` vars.
- Set custom player ssh password (optional): modify this line in `build/Dockerfile`:  
    - `RUN echo 'root:password' | chpasswd`
- Player internet access: the player container sits alone on the `br-ctf` Docker bridge (`172.29.250.0/24`) and gets public internet only. `./ctf start` installs host iptables rules (`CTF-EGRESS` chain, `INPUT` drop) that block private/link-local/CGNAT ranges (host, LAN, other team VMs, cloud metadata) and outbound SMTP; `./ctf stop` removes them. The player is root with `NET_ADMIN`, so these rules must stay on the host.
    - If the VM has a public IP or other team VMs are on public addresses, also add the provider's VM subnet to `EGRESS_BLOCKED_NETS` in `ctf`.
    - Delete or sparse-checkout `solution/` and `metadata/` on team VMs.
- Setup run on startup (optional): use provided service file
- Run `./ctf start` as root
- If you don't see any alarming output, it should be all good.  If you want, SSH into `root@<host-ip>` at the forwarded port (not `localhost`) and run commands from WiFi challenge 1 to make sure the player container is working.
    - Also check that any other service dockers are running
