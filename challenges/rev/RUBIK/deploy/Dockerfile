# Hosts the HELPER tesseract (complex_calibration_tesseract) in a browser.
#
# The helper is an OpenGL/pygame GUI app, so we give it a virtual X display
# (Xvfb) with software OpenGL (Mesa llvmpipe), capture that display with x11vnc,
# and expose it over the web with noVNC/websockify. Competitors open a URL and
# see/interact with the always-on 4D "diagnostic" view. It does NOT auto-solve:
# the flag only appears if the puzzle is actually solved, same as the download.
#
# Build context is the challenge root (Submission/Tesseract/), so this file can
# reach both dist/ and deploy/. docker-compose.yml sets that context and points
# `dockerfile:` at deploy/Dockerfile. COPY paths below are relative to that root.
# kali-rolling: the helper needs glibc >= 2.38 and SDL >= 2.32.64 (its bundled
# pygame refuses an older SDL); bookworm and trixie are both too old.
FROM kalilinux/kali-rolling

# Xvfb + software GL + VNC + noVNC, plus the shared libs the Nuitka/pygame/SDL
# onefile binary loads at runtime (it bundles Python, not these system libs).
# Retries help on slow or flaky networks.
RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        xvfb x11vnc novnc websockify \
        mesa-utils libgl1-mesa-dri libglx-mesa0 libglu1-mesa \
        libx11-6 libxext6 libxrender1 libxrandr2 libxi6 libxcursor1 libxinerama1 \
        libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-ttf-2.0-0 \
        libfreetype6 libpng16-16 libjpeg62-turbo fonts-dejavu-core \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user; the binary needs no privileges.
RUN useradd --create-home --shell /bin/bash tess
WORKDIR /home/tess

# The helper binary (always-on 4D view, no Space-solve).
COPY --chown=tess:tess dist/complex_calibration_tesseract /home/tess/helper
COPY --chown=tess:tess deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /home/tess/helper /entrypoint.sh

# Software OpenGL so no GPU is required on the host.
ENV LIBGL_ALWAYS_SOFTWARE=1 \
    GALLIUM_DRIVER=llvmpipe \
    SDL_VIDEO_X11_VISUALID=0x21 \
    DISPLAY=:0 \
    SCREEN=1280x800x24

USER tess
EXPOSE 6080
CMD ["/entrypoint.sh"]
