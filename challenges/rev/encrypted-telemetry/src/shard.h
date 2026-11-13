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

#define RS_TIER    3
#define RS_WAVES   5
#define RS_PER_WAVE 16
#define RS_DRONES  (RS_WAVES * RS_PER_WAVE)

static const uint8_t rs_ta[32] = {
    0x1b, 0x9c, 0x6c, 0x28, 0x72, 0x46, 0x29, 0x3c, 0x73, 0x82, 0x03, 0x57, 0x07, 0xda, 0x64, 0x7a,
    0x18, 0x6e, 0x17, 0xeb, 0x1b, 0xbb, 0xd9, 0xe2, 0x0b, 0xcd, 0x7b, 0x26, 0xc9, 0x46, 0xde, 0x27,
};
static const uint8_t rs_tb[32] = {
    0xaf, 0x4e, 0x73, 0x95, 0x77, 0x5e, 0x98, 0xaf, 0x8c, 0x40, 0xca, 0x5b, 0x7c, 0x2f, 0x60, 0xe5,
    0x4c, 0xf8, 0x46, 0x93, 0x3f, 0x77, 0xad, 0x19, 0x08, 0x84, 0xb0, 0xdb, 0xc8, 0x22, 0x63, 0x03,
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
