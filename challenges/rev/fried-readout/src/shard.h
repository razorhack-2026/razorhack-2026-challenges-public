/* Rogue Swarm shard scheme, shared by the game and the build-time generator.
 *
 * No flag string exists in the shipped binary. Each enemy (the escorts and the
 * Harvester) carries a 16-byte shard derived from its ID and a per-tier secret;
 * the game releases a shard only when that enemy is shot down. Shards XOR into
 * an accumulator, and once every enemy is down, key = SHA-256(acc || "RS-T" ||
 * tier) opens the embedded ChaCha20-Poly1305 ciphertext. Skipping kills
 * (patching the win check, editing the kill counter) leaves the accumulator
 * wrong and the AEAD tag fails.
 */
#ifndef RS_SHARD_H
#define RS_SHARD_H

#include <stdint.h>
#include <string.h>
#include <sodium.h>

#define RS_TIER    2
#define RS_ESCORTS 12
#define RS_BOSS_ID RS_ESCORTS               /* the Harvester's shard ID */
#define RS_DRONES  (RS_ESCORTS + 1)         /* every shard-carrying enemy */

static const uint8_t rs_ta[32] = {
    0xea, 0x1b, 0xbf, 0x20, 0x3e, 0xcc, 0xd6, 0x1f, 0x8b, 0x92, 0xbf, 0x3e, 0xcb, 0x22, 0x90, 0x9a,
    0x49, 0xa8, 0x53, 0x8a, 0x5f, 0x17, 0xaf, 0x85, 0x40, 0x45, 0x9a, 0xa0, 0x7a, 0x30, 0x6a, 0x8c,
};
static const uint8_t rs_tb[32] = {
    0x8a, 0xa3, 0x6c, 0xa6, 0x00, 0x31, 0x36, 0xaa, 0x8f, 0x7f, 0x2f, 0x4d, 0x2d, 0xfe, 0x43, 0x00,
    0x41, 0x5d, 0x48, 0x12, 0x1c, 0x28, 0x55, 0x05, 0x6a, 0xb7, 0x60, 0x27, 0x0c, 0xf3, 0x3d, 0x81,
};

/* Per-tier secret, rebuilt at run time from the two tables and an LCG stream. */
static void rs_secret(uint8_t out[32])
{
    uint32_t s = 0x9e3779b9u ^ (RS_TIER * 0x85ebca6bu);
    for (int i = 0; i < 32; i++) {
        s = s * 1664525u + 1013904223u;
        uint8_t b = rs_tb[(i * 7) & 31];
        int r = i % 5;
        b = (uint8_t)((b << r) | (b >> ((8 - r) & 7)));
        out[i] = rs_ta[i] ^ b ^ (uint8_t)(s >> 24);
    }
}

static void rs_shard(uint32_t id, uint8_t out[16])
{
    uint8_t buf[32 + 1 + 4], h[crypto_hash_sha256_BYTES];
    rs_secret(buf);
    buf[32] = RS_TIER;
    buf[33] = (uint8_t)id;
    buf[34] = (uint8_t)(id >> 8);
    buf[35] = (uint8_t)(id >> 16);
    buf[36] = (uint8_t)(id >> 24);
    crypto_hash_sha256(h, buf, sizeof buf);
    memcpy(out, h, 16);
    sodium_memzero(buf, sizeof buf);
    sodium_memzero(h, sizeof h);
}

static void rs_key(const uint8_t acc[16], uint8_t key[32])
{
    uint8_t buf[16 + 5];
    memcpy(buf, acc, 16);
    memcpy(buf + 16, "RS-T", 4);
    buf[20] = RS_TIER;
    crypto_hash_sha256(key, buf, sizeof buf);
    sodium_memzero(buf, sizeof buf);
}

static void rs_nonce(uint8_t nonce[crypto_aead_chacha20poly1305_ietf_NPUBBYTES])
{
    uint8_t h[crypto_hash_sha256_BYTES], tag[] = { 'r', 's', 'n', RS_TIER };
    crypto_hash_sha256(h, tag, sizeof tag);
    memcpy(nonce, h, crypto_aead_chacha20poly1305_ietf_NPUBBYTES);
}

#endif
