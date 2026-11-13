#!/bin/bash
/usr/sbin/sshd
echo "[eng-ws] sshd up; starting PLC runtime"
exec /opt/plc/plcd
