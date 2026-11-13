/* rtu_server.c — RazerPowerCo Field RTU firmware (fw 1.1.0)  INTENTIONALLY VULNERABLE
 *
 * RazorHack 2026 "Overburden" — stack overflow -> ret2win, but AI-hardened:
 * the vulnerable WRITE path is GATED behind a per-connection unlock. The service
 * hands out a random session token on IDENT; WRITE only arms after you answer
 * (token XOR UNLOCK_KEY). A solver working from the binary ALONE can't produce a
 * working exploit -- it never sees the per-session token -- so you must interact
 * with the live service. Binary is shipped stripped (no svc_dump_key symbol).
 */
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>

#define TAG_BUF    64
#define FLAG_PATH  "flag.txt"        /* production deployment reads "/flag" */
#define UNLOCK_KEY 0x49434152u       /* 'ICAR' — XOR transform applied to the token */

enum { CMD_IDENT = 0x10, CMD_READ = 0x20, CMD_WRITE = 0x30, CMD_UNLOCK = 0x40 };

static const char BANNER[] =
    "RazerPowerCo Field RTU / ICARUS Extraction Node / fw 1.1.0\n";

static uint32_t g_token;      /* per-connection session token (issued on IDENT) */
static int      g_unlocked;   /* WRITE stays locked until the token is answered */

static int read_n(void *dst, size_t n) {
    uint8_t *p = dst; size_t g = 0;
    while (g < n) { ssize_t r = read(0, p + g, n - g); if (r <= 0) return -1; g += (size_t)r; }
    return 0;
}
static void write_all(const void *src, size_t n) {
    const uint8_t *p = src; size_t s = 0;
    while (s < n) { ssize_t w = write(1, p + s, n - s); if (w <= 0) return; s += (size_t)w; }
}
static void drain(uint16_t n) { uint8_t d; while (n--) if (read_n(&d, 1)) _exit(0); }

static void emit_token(void) {
    static const char H[] = "0123456789abcdef";
    char b[] = "SESSION=00000000\n";
    for (int i = 0; i < 8; i++) b[8 + i] = H[(g_token >> (28 - 4 * i)) & 0xf];
    write_all(b, sizeof b - 1);
}

/* Reachable only by hijacking control flow. Symbol is stripped from the shipped binary. */
__attribute__((used))
static void svc_dump_key(void) {
    char flag[128];
    int f = open(FLAG_PATH, O_RDONLY);
    if (f < 0) { write_all("[RTU] maintenance key unavailable\n", 34); _exit(1); }
    ssize_t n = read(f, flag, sizeof flag);
    if (n > 0) write_all(flag, (size_t)n);
    _exit(0);
}

static void handle_ident(void) {
    write_all(BANNER, sizeof BANNER - 1);
    emit_token();                                  /* token only observable on the wire */
}

static void handle_unlock(uint16_t len) {
    if (len != 4) { drain(len); write_all("[RTU] denied\n", 13); return; }
    uint8_t p[4];
    if (read_n(p, 4)) _exit(0);
    uint32_t got = (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
    if (got == (g_token ^ UNLOCK_KEY)) { g_unlocked = 1; write_all("[RTU] maintenance mode enabled\n", 31); }
    else                               { write_all("[RTU] denied\n", 13); }
}

static void handle_read(uint16_t len) {
    uint8_t p[64]; if (len > sizeof p) len = sizeof p;
    if (read_n(p, len)) _exit(0);
    uint8_t resp[6] = { 'V','A','L','=', 0x00, 0x2A };
    write_all(resp, sizeof resp);
}

/* VULNERABLE: unbounded copy into a 64-byte stack buffer. Only reached after unlock. */
static void handle_write(uint16_t len) {
    char buf[TAG_BUF]; uint8_t tag[2];
    if (len < 2) _exit(0);
    if (read_n(tag, 2)) _exit(0);
    uint16_t vlen = (uint16_t)(len - 2);
    if (read_n(buf, vlen)) _exit(0);               /* <-- overflow when vlen > 64 */
    write_all("[RTU] tag written\n", 18);
}

static uint32_t gen_token(void) {
    uint32_t t = 0; int f = open("/dev/urandom", O_RDONLY);
    if (f >= 0) { if (read(f, &t, sizeof t) != (ssize_t)sizeof t) t = 0; close(f); }
    return t ? t : 0x0badc0deu;
}

int main(void) {
    alarm(30);
    g_token = gen_token();
    for (;;) {
        uint8_t hdr[5];
        if (read_n(hdr, 5)) return 0;
        if (hdr[0] != 'R' || hdr[1] != 'P') return 0;       /* MAGIC "RP" */
        uint8_t  cmd = hdr[2];
        uint16_t len = (uint16_t)((hdr[3] << 8) | hdr[4]);  /* big-endian */
        switch (cmd) {
            case CMD_IDENT:  handle_ident();   break;
            case CMD_READ:   handle_read(len); break;
            case CMD_UNLOCK: handle_unlock(len); break;
            case CMD_WRITE:
                if (!g_unlocked) {                          /* GATE: no unlock, no overflow */
                    write_all("[RTU] locked -- maintenance auth required\n", 42);
                    drain(len);
                    break;
                }
                handle_write(len);
                break;
            default: return 0;
        }
    }
}
