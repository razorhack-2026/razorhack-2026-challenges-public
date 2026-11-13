# Board A (Extraction Gateway) — INTENTIONALLY VULNERABLE.
# NX / no canary / no PIE / CET off; stripped (win function found by RE).
# -fcf-protection=none is REQUIRED (CET shadow stack otherwise blocks the ret2win).
CC     ?= gcc
CFLAGS := -O0 -fno-stack-protector -no-pie -z noexecstack -fcf-protection=none
BIN    := rtu_server

$(BIN): rtu_server.c
	$(CC) $(CFLAGS) -o $@ $<
	strip $@

.PHONY: clean
clean:
	rm -f $(BIN)
