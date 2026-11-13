// lenscal — "lens calibration" utility for Flat Field (RazorHack 2026, Rev).
//
// GM build input. Compiled static + stripped into dist/lenscal; this source is
// never shipped. It embeds an opaque calibration mask (a CAL1 file made by
// make_payload.py) into a frame's blue-channel low bits at PRNG-chosen pixels.
//
// Build (from Windows, via zig):
//   zig cc -target x86_64-linux-musl -O2 -s -static -o ../dist/lenscal lenscal.c -lm

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#include "stb_image.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CAL_MAGIC 0x314C4143u /* "CAL1" little-endian */

static uint32_t rng_state;

static uint32_t rng_next(void) {
    uint32_t x = rng_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return rng_state = x;
}

// Seed depends only on the red channel and the frame size, so it is the same
// before and after calibration (only blue is touched).
static uint32_t frame_seed(const uint8_t *px, int w, int h) {
    uint32_t hsh = 0x811C9DC5u;
    size_t n = (size_t)w * h;
    for (size_t i = 0; i < n; i++) {
        hsh ^= px[i * 3];
        hsh *= 0x01000193u;
    }
    hsh ^= ((uint32_t)w << 16) | (uint32_t)h;
    hsh ^= 0x4C454E53u; /* "LENS" */
    return hsh ? hsh : 1;
}

static uint8_t *read_file(const char *path, size_t *len) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = malloc(sz > 0 ? (size_t)sz : 1);
    if (buf && fread(buf, 1, (size_t)sz, f) != (size_t)sz) { free(buf); buf = NULL; }
    fclose(f);
    *len = (size_t)sz;
    return buf;
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <frame.png> <mask.cal> <out.png>\n", argv[0]);
        return 1;
    }

    int w, h, comp;
    uint8_t *px = stbi_load(argv[1], &w, &h, &comp, 3);
    if (!px) {
        fprintf(stderr, "lenscal: cannot read frame '%s'\n", argv[1]);
        return 1;
    }

    size_t mlen;
    uint8_t *mask = read_file(argv[2], &mlen);
    if (!mask || mlen < 8) {
        fprintf(stderr, "lenscal: cannot read calibration mask '%s'\n", argv[2]);
        return 1;
    }

    uint32_t magic;
    uint16_t mw, mh;
    memcpy(&magic, mask, 4);
    memcpy(&mw, mask + 4, 2);
    memcpy(&mh, mask + 6, 2);
    size_t need = 8 + ((size_t)mw * mh + 7) / 8;
    if (magic != CAL_MAGIC || mlen != need) {
        fprintf(stderr, "lenscal: bad calibration mask\n");
        return 1;
    }

    size_t npix = (size_t)w * h;
    size_t nbits = mlen * 8;
    if (nbits > npix / 4) {
        fprintf(stderr, "lenscal: frame too small for mask\n");
        return 1;
    }

    uint8_t *used = calloc(npix, 1);
    if (!used) return 1;

    rng_state = frame_seed(px, w, h);
    fprintf(stderr, "lenscal: frame %dx%d, mask %ux%u\n", w, h, mw, mh);

    for (size_t i = 0; i < nbits; i++) {
        int bit = (mask[i >> 3] >> (7 - (i & 7))) & 1;

        size_t idx;
        do {
            idx = rng_next() % npix;
        } while (used[idx]);
        used[idx] = 1;

        uint8_t k = rng_next() & 3;
        uint8_t *b = &px[idx * 3 + 2];
        *b = (uint8_t)((*b & ~3u) | (bit ? (k ^ 3u) : k));
    }

    if (!stbi_write_png(argv[3], w, h, 3, px, w * 3)) {
        fprintf(stderr, "lenscal: cannot write '%s'\n", argv[3]);
        return 1;
    }
    fprintf(stderr, "lenscal: calibration applied -> %s\n", argv[3]);

    free(used);
    free(mask);
    stbi_image_free(px);
    return 0;
}
