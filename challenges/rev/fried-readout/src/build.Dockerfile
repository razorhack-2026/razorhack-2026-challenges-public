# Build environment for Fried Readout. bookworm's glibc (2.36) keeps the binary
# runnable on older Kali images.
#
#   docker build -t rs-build -f src/build.Dockerfile src
#   docker run --rm -v "$PWD":/work rs-build make
FROM debian:bookworm
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential cmake git ca-certificates \
      libx11-dev libxrandr-dev libxcursor-dev libxinerama-dev libxi-dev libxext-dev libgl1-mesa-dev \
      libsodium-dev
WORKDIR /work
