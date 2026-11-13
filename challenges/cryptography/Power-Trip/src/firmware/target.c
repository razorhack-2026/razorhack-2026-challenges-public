/* RPC-IC220 interlock controller -- bench harness entry point.
 *
 * The rig writes the key and plaintext into the IO block at 0x20000000, starts
 * the core at the reset vector, and reads the ciphertext back out. The trigger
 * register at 0x40000000 is the GPIO the board raises around the AES call; the
 * rig watches it to know when to arm and disarm the shunt capture.
 */
#include <stdint.h>

/* The IO block sits in its own region, not in SRAM -- see link.ld. */
#define IO_BASE   0x30000000u
#define TRIG_ADDR 0x40000000u

#define FRAME_LEN 512

typedef struct {
    volatile uint8_t key[16];   /* 0x30000000 -- written by the rig  */
    volatile uint8_t pt[16];    /* 0x30000010 -- written by the rig  */
    volatile uint8_t ct[16];    /* 0x30000020 -- read back by the rig */
    volatile uint16_t crc;      /* 0x30000030 -- request frame CRC    */
} io_t;

#define IO   ((io_t *)IO_BASE)
#define TRIG (*(volatile uint32_t *)TRIG_ADDR)

void aes_key_expansion(const volatile uint8_t *key);
void aes_encrypt_block(const volatile uint8_t *pt, volatile uint8_t *ct);

/* Request staging buffer. Lives in SRAM alongside the cipher state. */
static volatile uint8_t frame[FRAME_LEN];

/* Expand the 16-byte request into the command frame the link layer validates. */
static void stage_request(void)
{
    int i;
    for (i = 0; i < FRAME_LEN; i++)
        frame[i] = (uint8_t)(IO->pt[i & 15] ^ (uint8_t)i);
}

static uint16_t crc16(const volatile uint8_t *p, int n)
{
    uint16_t c = 0xFFFF;
    int i, b;

    for (i = 0; i < n; i++) {
        c ^= p[i];
        for (b = 0; b < 8; b++)
            c = (c & 1) ? (uint16_t)((c >> 1) ^ 0xA001) : (uint16_t)(c >> 1);
    }
    return c;
}

void aes_main(void)
{
    /* Key schedule runs outside the trigger window: on the real board the
     * schedule is computed once at boot, not per authentication request.
     * Keeping it out also keeps the round keys -- which are identical in every
     * capture -- from being averaged out of the noise across a trace set. */
    aes_key_expansion(IO->key);

    /* The trigger covers the whole authentication routine, not just the
     * cipher: frame staging and CRC validation run first, exactly as they
     * would on a real request. That is why the operation is longer than the
     * scope's capture depth, and why the offset has to be chosen. */
    TRIG = 1;
    stage_request();
    IO->crc = crc16(frame, FRAME_LEN);
    aes_encrypt_block(IO->pt, IO->ct);
    TRIG = 0;
}

__attribute__((naked, section(".text.entry")))
void _start(void)
{
    __asm__ volatile(
        "ldr r0, =_stack_top\n"
        "mov sp, r0\n"
        "bl  aes_main\n"
        "b   .\n"
    );
}
