# Enki's Tongue -- build the shipped artifacts into dist/
#
#   make            build dist/enkivm (stripped) + dist/enki.nam + SHA256SUMS
#   make verify     rebuild, then run the Z3 official solver end-to-end
#   make clean
#
# enki.nam is generated deterministically by build.py (fixed SEED), so a clean
# rebuild reproduces byte-identical artifacts. `make verify` needs z3-solver:
#   pip install z3-solver     (then: make verify PY=/path/to/venv/python)

CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra -std=c11
PY      ?= python3
DIST    := dist
VM      := $(DIST)/enkivm
NAM     := $(DIST)/enki.nam

.PHONY: all verify clean
all: $(DIST)/SHA256SUMS

$(VM): src/enkivm.c | $(DIST)
	$(CC) $(CFLAGS) -o $@ $<
	strip $@                       # ship stripped: recon is reversing the ISA

$(NAM): src/build.py | $(DIST)
	python3 src/build.py $@

$(DIST):
	mkdir -p $(DIST)

$(DIST)/SHA256SUMS: $(VM) $(NAM)
	cd $(DIST) && sha256sum enkivm enki.nam > SHA256SUMS

verify: all
	$(PY) solution/solve.py $(NAM) $(VM)

clean:
	rm -f $(VM) $(NAM) $(DIST)/SHA256SUMS
