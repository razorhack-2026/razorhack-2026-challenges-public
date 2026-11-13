# Fried Readout (Rogue Swarm tier 2) -- build the shipped binary into dist/
#
#   make            build dist/fried_readout (stripped, PIE) + SHA256SUMS
#   make verify     rebuild, then run the reference solver end-to-end under Xvfb
#   make clean      remove built artifacts
#
# Build deps (Debian): see src/build.Dockerfile (bookworm + cmake, git, X11
#   dev headers, libsodium-dev). The first `make` clones raylib $(RAYLIB_TAG)
#   and builds it static with the rlsw CPU renderer (PLATFORM=RGFW,
#   OPENGL_VERSION=Software), so the game needs no GPU or libGL.
# Verify deps: xvfb xauth xdotool python3 (imagemagick optional, end screenshot)
#
# Build on an OLD glibc (debian:bookworm, 2.36) so the binary runs on older
# Kali images. A kali-rolling build (glibc 2.43) refuses to start on Kali
# 2026.2 (glibc 2.42) -- checked 2026-11-03.
#
# The flag is read from challenge.yml and sealed by build/gen into build/ct.h;
# the shipped binary holds only the ciphertext. raylib and libsodium are linked
# statically, so the binary needs only glibc, libX11, libXrandr and libGL at run
# time (libGL is linked but unused; rendering is on the CPU).

CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra -std=c11
BUILD   := build
DIST    := dist
BIN     := $(DIST)/fried_readout
FLAG    := $(shell sed -n 's/^ *- *\(flag{.*}\) *$$/\1/p' challenge.yml)

RAYLIB_TAG := 6.2
RAYLIB_DIR := $(BUILD)/raylib-$(RAYLIB_TAG)
RAYLIB_LIB := $(RAYLIB_DIR)/inst/lib/libraylib.a

.PHONY: all verify clean
all: $(DIST)/SHA256SUMS

$(RAYLIB_LIB): | $(BUILD)
	git clone -q --depth 1 --branch $(RAYLIB_TAG) https://github.com/raysan5/raylib.git $(RAYLIB_DIR)/src
	cmake -S $(RAYLIB_DIR)/src -B $(RAYLIB_DIR)/build -DPLATFORM=RGFW -DOPENGL_VERSION=Software \
	    -DWITH_PIC=ON -DBUILD_EXAMPLES=OFF -DCMAKE_BUILD_TYPE=Release \
	    -DCMAKE_INSTALL_PREFIX=$(abspath $(RAYLIB_DIR))/inst -DCMAKE_INSTALL_LIBDIR=lib
	cmake --build $(RAYLIB_DIR)/build -j
	cmake --install $(RAYLIB_DIR)/build

$(BUILD)/gen: src/gen.c src/shard.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ src/gen.c -lsodium

$(BUILD)/ct.h: $(BUILD)/gen challenge.yml
	$(BUILD)/gen '$(FLAG)' > $@

$(BIN): src/fried_readout.c src/shard.h $(BUILD)/ct.h $(RAYLIB_LIB) | $(DIST)
	$(CC) $(CFLAGS) -fPIE -pie -I$(BUILD) -I$(RAYLIB_DIR)/inst/include -o $@ src/fried_readout.c \
	    $(RAYLIB_LIB) -Wl,-Bstatic -lsodium -Wl,-Bdynamic -lX11 -lXrandr -lGL -lm -lpthread -ldl
	# -lGL only resolves RGFW's GLX code, which raylib 6.2 compiles in even with
	# OPENGL_VERSION=Software; it is never called. Cheat Engine's Qt6 needs libGL
	# anyway, so any box that runs CE has it.
	strip $@                       # ship stripped: the lesson is the memory scan, not symbols

$(BUILD) $(DIST):
	mkdir -p $@

$(DIST)/SHA256SUMS: $(BIN)
	cd $(DIST) && sha256sum fried_readout > SHA256SUMS

verify: all
	xvfb-run -a -s "-screen 0 640x720x24" python3 solution/solve.py $(BIN) '$(FLAG)'

clean:
	rm -rf $(BUILD) $(BIN) $(DIST)/SHA256SUMS
