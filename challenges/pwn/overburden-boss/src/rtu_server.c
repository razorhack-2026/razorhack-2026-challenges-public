/* rtu_server.c — RazerPowerCo Field RTU / Extraction GATEWAY (fw 2.0.0)  VULNERABLE
 *
 * Board A of a two-board setup. Player-facing on stdin/stdout (socat fork). Holds an
 * internal upstream link to Board B (the extraction master — a BLACK BOX, no binary).
 *   - POLL (0x20): benign, read-only telemetry relayed from B (see the process).
 *   - WRITE (0x30): unbounded stack copy -> ret2win into enter_relay_mode(), which
 *     pipes you transparently to B. That is the PIVOT.
 * There is NO flag in A. The maintenance key lives in B and only comes out when B's
 * process is driven to SAFE. Ship stripped; No PIE / no canary / NX / -fcf-protection=none.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/select.h>

#define TAG_BUF 64

static int up_fd = -1;                 /* upstream link to Board B */

static int read_n(int fd, void *dst, size_t n) {
    uint8_t *p = dst; size_t g = 0;
    while (g < n) { ssize_t r = read(fd, p + g, n - g); if (r <= 0) return -1; g += (size_t)r; }
    return 0;
}
static void write_all(int fd, const void *src, size_t n) {
    const uint8_t *p = src; size_t s = 0;
    while (s < n) { ssize_t w = write(fd, p + s, n - s); if (w <= 0) return; s += (size_t)w; }
}

static const char BANNER[] =
    "RazerPowerCo Field RTU / ICARUS Extraction Gateway / fw 2.0.0\n";

/* --- upstream (Board B) --- */
static int mb_read(uint8_t reg, uint16_t *out) {
    if (up_fd < 0) return -1;
    uint8_t req[4] = { 'M','B','R', reg };
    write_all(up_fd, req, 4);
    uint8_t r[2];
    if (read_n(up_fd, r, 2)) return -1;
    *out = (uint16_t)((r[0] << 8) | r[1]);
    return 0;
}

static void handle_ident(void) { write_all(1, BANNER, sizeof BANNER - 1); }

/* Benign observation path: relay a few read-only registers from B. */
static void handle_poll(void) {
    uint16_t p = 0, t = 0, m = 0;
    if (mb_read(0x00, &p) || mb_read(0x01, &t) || mb_read(0x05, &m)) {
        write_all(1, "[RTU] upstream link down\n", 25); return;
    }
    dprintf(1, "PRESSURE=%u TEMP=%u MODE=%u\n", p, t, m);
}

/* Never called on any path — the pivot. Pipes the player transparently to Board B. */
__attribute__((used))
static void enter_relay_mode(void) {
    if (up_fd < 0) _exit(1);
    char buf[1024];
    int mx = up_fd > 0 ? up_fd : 0;
    for (;;) {
        fd_set rfds; FD_ZERO(&rfds); FD_SET(0, &rfds); FD_SET(up_fd, &rfds);
        if (select(mx + 1, &rfds, NULL, NULL, NULL) < 0) _exit(0);
        if (FD_ISSET(0, &rfds)) {
            ssize_t n = read(0, buf, sizeof buf); if (n <= 0) _exit(0);
            write_all(up_fd, buf, (size_t)n);
        }
        if (FD_ISSET(up_fd, &rfds)) {
            ssize_t n = read(up_fd, buf, sizeof buf); if (n <= 0) _exit(0);
            write_all(1, buf, (size_t)n);
        }
    }
}

/* VULNERABLE: unbounded copy into a 64-byte stack buffer. ret2win -> enter_relay_mode. */
static void handle_write(uint16_t len) {
    char buf[TAG_BUF]; uint8_t tag[2];
    if (len < 2) _exit(0);
    if (read_n(0, tag, 2)) _exit(0);
    uint16_t vlen = (uint16_t)(len - 2);
    if (read_n(0, buf, vlen)) _exit(0);        /* <-- overflow when vlen > 64 */
    write_all(1, "[RTU] tag written\n", 18);
}

static void connect_upstream(void) {
    const char *h = getenv("B_HOST"); const char *ps = getenv("B_PORT");
    int port = ps ? atoi(ps) : 9001;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return;
    struct sockaddr_in sa; memset(&sa, 0, sizeof sa);
    sa.sin_family = AF_INET; sa.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, h ? h : "127.0.0.1", &sa.sin_addr) != 1) { close(fd); return; }
    if (connect(fd, (struct sockaddr *)&sa, sizeof sa) != 0) { close(fd); return; }
    up_fd = fd;
}

int main(void) {
    alarm(300);                /* generous idle/session cap: scripted solves finish in ms;
                                  humans need room to probe the master's process by hand */
    connect_upstream();
    for (;;) {
        uint8_t hdr[5];
        if (read_n(0, hdr, 5)) return 0;
        if (hdr[0] != 'R' || hdr[1] != 'P') return 0;
        uint8_t  cmd = hdr[2];
        uint16_t len = (uint16_t)((hdr[3] << 8) | hdr[4]);
        switch (cmd) {
            case 0x10: handle_ident(); break;
            case 0x20: handle_poll();  break;
            case 0x30: handle_write(len); break;
            default: return 0;
        }
    }
}
