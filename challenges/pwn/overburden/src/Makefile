# Overburden — RazerPowerCo Field RTU firmware (INTENTIONALLY VULNERABLE)
# Hard tier protections: NX on, no stack canary, no PIE, CET disabled.
# -fcf-protection=none is REQUIRED: on CET-capable hosts the shadow stack
# otherwise catches the ret2win at the `ret`. See ../solution/SOLUTION.md.
# The shipped binary is STRIPPED (no svc_dump_key symbol) — the solver must
# find the win function by RE. Addresses are fixed anyway (No PIE); stripping
# does not move code, so svc_dump_key stays at its link-time address.
CC     ?= gcc
CFLAGS := -O0 -fno-stack-protector -no-pie -z noexecstack -fcf-protection=none
BIN    := rtu_server

$(BIN): rtu_server.c
	$(CC) $(CFLAGS) -o $@ $<
	strip $@

.PHONY: check clean
check: $(BIN)
	@command -v checksec >/dev/null 2>&1 && checksec --file=$(BIN) || \
	  { echo "(checksec absent) readelf summary:"; readelf -lh $(BIN) | grep -E 'Type:|GNU_STACK'; }

clean:
	rm -f $(BIN)
