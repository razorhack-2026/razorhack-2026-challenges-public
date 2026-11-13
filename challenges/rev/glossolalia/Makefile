# Glossolalia -- build the shipped artifacts into dist/
#
#   make            build dist/enkivm (stripped) + dist/asherah.nam + SHA256SUMS
#   make verify     rebuild, then run the official solver end-to-end
#   make clean      remove built artifacts
#
# asherah.nam is generated deterministically by build.py (fixed RNG seed), so a
# clean rebuild reproduces byte-identical artifacts and checksums.

CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra -std=c11
DIST    := dist
VM      := $(DIST)/enkivm
NAM     := $(DIST)/asherah.nam

.PHONY: all verify clean
all: $(DIST)/SHA256SUMS

$(VM): src/enkivm.c | $(DIST)
	$(CC) $(CFLAGS) -o $@ $<
	strip $@                       # ship stripped: recon is reversing the ISA, not reading symbols

$(NAM): src/build.py | $(DIST)
	python3 src/build.py $@

$(DIST):
	mkdir -p $(DIST)

$(DIST)/SHA256SUMS: $(VM) $(NAM)
	cd $(DIST) && sha256sum enkivm asherah.nam > SHA256SUMS

verify: all
	python3 solution/solve.py $(NAM) $(VM)

clean:
	rm -f $(VM) $(NAM) $(DIST)/SHA256SUMS
