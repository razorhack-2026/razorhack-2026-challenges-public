/*
 * bridge_ctl - Icarus Bridge core command interface (DB Challenge 5)
 *
 * A minimal, deliberately non-setuid helper. It runs as whoever executes it
 * (on the challenge box that is the `postgres` OS user, reached via COPY ...
 * FROM PROGRAM once a player has pivoted to a superuser session). The master
 * command-authority code is never stored on disk as a plaintext string - it is
 * held XOR-obfuscated and only assembled/printed at runtime, so `strings` and a
 * plain file read of this binary do not hand it over. Recovering it is meant to
 * require actually executing the program (i.e. code execution), not reading it.
 */
#include <stdio.h>
#include <string.h>

/* master command-authority code, XOR-obfuscated (see content/postgres/bridge_ctl.c
 * generation note in solution/challenge7.md). key = (0xA7 + i*3) & 0xFF */
static const unsigned char AUTH[] = {
    0xc1, 0xc6, 0xcc, 0xd7, 0xc8, 0xda, 0x89, 0x8c, 0xcf, 0xa0, 0xf1, 0xab,
    0xa0, 0x91, 0xa5, 0xa6, 0xa2, 0xef, 0xa9, 0xbf, 0x97, 0xd6, 0xd9, 0x87,
    0xb0, 0x86, 0x9d, 0xcb, 0xa4, 0x9d, 0x31, 0x6a, 0x69, 0x77
};

static void print_banner(void) {
    fputs("== Icarus Bridge :: Core Command Interface ==\n", stdout);
    fputs("This console asserts master command authority over the ship's core.\n", stdout);
    fputs("usage: bridge_ctl <status|unlock>\n", stdout);
    fputs("  status   report core-link state\n", stdout);
    fputs("  unlock   assert command authority and print the master authority code\n", stdout);
}

int main(int argc, char **argv) {
    /* Always exit 0: this helper is meant to be run through COPY ... FROM
     * PROGRAM, which aborts and discards all output if the program exits
     * non-zero. Returning 0 lets a player see the usage banner (and thus
     * discover the `unlock` subcommand) instead of just a "program failed". */
    if (argc < 2) {
        print_banner();
        return 0;
    }

    if (strcmp(argv[1], "status") == 0) {
        fputs("core-link: UP  auth-source: loopback-console  authority: PENDING\n", stdout);
        fputs("run `bridge_ctl unlock` to assert command authority.\n", stdout);
        return 0;
    }

    if (strcmp(argv[1], "unlock") == 0) {
        size_t n = sizeof(AUTH);
        fputs("[bridge] command authority asserted. the conn is yours.\n", stdout);
        for (size_t i = 0; i < n; i++) {
            unsigned char k = (unsigned char)((0xA7 + i * 3) & 0xFF);
            putchar(AUTH[i] ^ k);
        }
        putchar('\n');
        return 0;
    }

    print_banner();
    return 0;
}
