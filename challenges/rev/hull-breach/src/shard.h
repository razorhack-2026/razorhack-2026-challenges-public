/* Rogue Swarm shard scheme, shared by the game and the build-time generator.
 *
 * No flag string exists in the shipped binary. Each drone carries a 16-byte
 * shard derived from its ID and a per-tier secret; the game releases a shard
 * only when that drone is shot down. Shards XOR into an accumulator, and once
 * every drone is down, key = SHA-256(acc || "RS-T" || tier) opens the embedded
 * ChaCha20-Poly1305 ciphertext. Skipping kills (patching the win check, editing
 * the kill counter) leaves the accumulator wrong and the AEAD tag fails.
 */
#ifndef RS_SHARD_H
#define RS_SHARD_H

#include <stdint.h>
#include <string.h>
#include <sodium.h>

#define RS_TIER    1
#define RS_WAVES   5
#define RS_PER_WAVE 16
#define RS_DRONES  (RS_WAVES * RS_PER_WAVE)

static const uint8_t rs_ta[32] = {
    0x67, 0x46, 0x89, 0xad, 0x4c, 0x9e, 0x33, 0x95, 0xd5, 0xf1, 0x52, 0x90, 0x7e, 0xba, 0xea, 0x90,
    0x8a, 0x70, 0x0f, 0xae, 0x00, 0xfa, 0xba, 0xeb, 0x29, 0x32, 0x7c, 0x41, 0x30, 0xe9, 0x17, 0xec,
};
static const uint8_t rs_tb[32] = {
    0xa7, 0x52, 0x2c, 0x1b, 0xa1, 0x3d, 0x13, 0xfe, 0x6a, 0xdd, 0xbc, 0x19, 0xa6, 0x4c, 0xec, 0x5d,
    0x87, 0xc2, 0xe1, 0x45, 0x53, 0x0b, 0x2d, 0x1c, 0x89, 0x67, 0xdd, 0x2c, 0xb6, 0x68, 0x93, 0xf0,
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
