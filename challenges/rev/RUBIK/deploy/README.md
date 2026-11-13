# Hosting the helper tesseract (browser view)

This deployment puts the **helper** tesseract (`complex_calibration_tesseract`,
the always-on 4D "diagnostic" view) in a browser so competitors can see the 4D
structure without a local OpenGL setup. It runs the GUI on a virtual X display
with software OpenGL (Mesa llvmpipe), captures it with VNC, and serves it over
noVNC.

This hosted view is delivered through the challenge's **unlockable hint**, not
`connection_info` — put this URL (and a download link for the helper binary) in
the hint so only teams who spend points get it. Don't advertise it openly.

**It does not help anyone cheat:** the helper is the *no-auto-solve* build. The
puzzle is still scrambled and must be solved by hand, and the flag only appears
on a genuine solve — hosting the view doesn't change that. The main challenge
binary (`complex_calibration`, which carries the flag) is a plain download and
is deliberately **not** part of this deployment.

## Run it

From `Submission/Tesseract/` (the challenge root, so the build can see `dist/`):

    docker compose up -d --build
    # then open http://<host>:6080

- Port `6080` is noVNC. Put it behind the event reverse proxy / firewall as you
  like; change `"6080:6080"` in `docker-compose.yml` for a different port.
- No GPU is needed (software rendering). It is CPU-bound, so if many teams open
  it at once consider one container per few teams, or cap CPU.

## Files

- `Dockerfile` — virtual display + software GL + VNC + noVNC, and the runtime
  libs the pygame/SDL/OpenGL binary loads.
- `entrypoint.sh` — starts Xvfb, (re)launches the helper, x11vnc, websockify.
- `../docker-compose.yml` — build context and port mapping.

## Caveats / TODO(WALL-D)

- **Untested in this environment.** Build and open it once before the event. If
  the window is black, the binary's GL/SDL needs a lib not installed here —
  check `docker compose logs` and `/tmp/helper.log` inside the container
  (`docker compose exec helper cat /tmp/helper.log`) and add the missing
  `apt-get` package.
- **Shared view.** `x11vnc -shared` means everyone who opens the URL drives the
  *same* window — one team's moves are visible to all. That's fine for a "watch
  the 4D view" aid, but if you want per-team isolation, run multiple containers
  on different ports, or switch to a per-session launcher.
- **Read-only option.** To stop visitors from moving the shared puzzle, add
  `-viewonly` to the `x11vnc` line in `entrypoint.sh`.
- The window size is `SCREEN` (default `1280x800x24`); the binary opens at 1200
  wide. Adjust `SCREEN` in the Dockerfile if you change the width.
