#!/bin/bash
# Start a virtual display, run the helper tesseract on it, and stream that
# display to the browser over noVNC. If the helper window is closed or crashes,
# it is relaunched so the hosted view stays up for the whole event.
set -e

: "${SCREEN:=1280x800x24}"
: "${DISPLAY:=:0}"
export DISPLAY

# Virtual framebuffer with GLX, so the OpenGL app has somewhere to draw.
Xvfb "$DISPLAY" -screen 0 "$SCREEN" +extension GLX +render -noreset &
# Wait for the display to come up.
for _ in $(seq 1 50); do
    xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && break
    sleep 0.1
done

# Keep the helper running. It is the no-auto-solve build: a scrambled puzzle
# that still has to be solved by hand, so the hosted view can't be used to
# reveal the flag by itself — it only helps competitors see the 4D structure.
( while true; do
    /home/tess/helper >/tmp/helper.log 2>&1 || true
    sleep 1
  done ) &

# Share the display read/write over VNC (localhost only; noVNC bridges to it).
x11vnc -display "$DISPLAY" -forever -shared -nopw -rfbport 5900 -localhost -quiet &

# noVNC on 6080 -> VNC on 5900. Path differs by distro; try both.
VNC_HTML=/usr/share/novnc
[ -f "$VNC_HTML/vnc.html" ] || VNC_HTML=/usr/share/webapps/novnc
# Make "/" open the client directly.
[ -f "$VNC_HTML/index.html" ] || ln -sf vnc.html "$VNC_HTML/index.html" 2>/dev/null || true

exec websockify --web="$VNC_HTML" 6080 localhost:5900
