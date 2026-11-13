#!/bin/bash
# Flush Docker-assigned IP
ip addr flush dev eth0

# Bring interface up (sometimes needed after flush)
ip link set eth0 up

# Start DHCP client
dhclient eth0 &

# Start apache server
# tail -f /dev/null
# apachectl -D FOREGROUND
