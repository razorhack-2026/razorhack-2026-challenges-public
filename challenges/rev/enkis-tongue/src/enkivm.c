/*
 * enkivm - interpreter for the recovered *me* artifact (Enki's Tongue).
 *
 * Same enki-VM family as the Glossolalia build, extended with one op: ROL
 * (32-bit rotate-left), which the stage-2 ARX flag cipher needs. Everything
 * challenge-specific lives in the .nam program, not here.
 *
 *   .nam layout (big-endian header):
 *     magic[4]   = "NAM\0"
 *     code_len   : u16   (bytes of code, multiple of 4)
 *     data_len   : u16   (bytes of data, loaded into tape at offset 0)
 *     code[code_len]
 *     data[data_len]
 *
 *   instruction = [op:1][a:1][b:1][imm:1]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define NREG        8
#define TAPE_SIZE   4096
#define MAX_CODE    65536
#define STEP_LIMIT  20000000UL   /* runaway guard */

enum {
    OP_HALT  = 0x00,
    OP_LOADI = 0x11,   /* reg[a] = imm                    */
    OP_MOV   = 0x22,   /* reg[a] = reg[b]                 */
    OP_ADD   = 0x33,   /* reg[a] = reg[a] + reg[b]        */
    OP_SUB   = 0x44,   /* reg[a] = reg[a] - reg[b]        */
    OP_XOR   = 0x55,   /* reg[a] = reg[a] ^ reg[b]        */
    OP_AND   = 0x66,   /* reg[a] = reg[a] & reg[b]        */
    OP_MIX   = 0x77,   /* reg[a] = tape[reg[a] & 0xFF]    (S-box at tape[0..255]) */
    OP_LOAD  = 0x88,   /* reg[a] = tape[reg[b]]           */
    OP_STORE = 0x99,   /* tape[reg[a]] = reg[b] & 0xFF    */
    OP_CMP   = 0xAA,   /* zf = (reg[a] == reg[b])         */
    OP_JMP   = 0xBB,   /* pc = (a<<8)|b                   */
    OP_JZ    = 0xCC,   /* if (zf)  pc = (a<<8)|b          */
    OP_JNZ   = 0xDD,   /* if (!zf) pc = (a<<8)|b          */
    OP_IN    = 0xEE,   /* reg[a] = next input byte, else 0 */
    OP_OUT   = 0xFF,   /* putchar(reg[a] & 0xFF)          */
    OP_ROL   = 0x1A    /* reg[a] = rotl32(reg[a], imm & 31)  (0 => identity) */
};

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s <incantation.nam>\n", argv[0]);
        return 2;
    }

    /* --- load the incantation --------------------------------------- */
    FILE *f = fopen(argv[1], "rb");
    if (!f) { fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }

    uint8_t hdr[8];
    if (fread(hdr, 1, 8, f) != 8 || memcmp(hdr, "NAM\0", 4) != 0) {
        fprintf(stderr, "not a nam-shub\n"); fclose(f); return 2;
    }
    uint32_t code_len = (hdr[4] << 8) | hdr[5];
    uint32_t data_len = (hdr[6] << 8) | hdr[7];
    if (code_len > MAX_CODE || (code_len & 3) || data_len > TAPE_SIZE) {
        fprintf(stderr, "malformed nam-shub\n"); fclose(f); return 2;
    }

    static uint8_t code[MAX_CODE];
    static uint8_t tape[TAPE_SIZE];
    if (fread(code, 1, code_len, f) != code_len ||
        fread(tape, 1, data_len, f) != data_len) {
        fprintf(stderr, "truncated nam-shub\n"); fclose(f); return 2;
    }
    fclose(f);

    /* --- slurp the spoken input (stdin) ----------------------------- */
    uint8_t *in = NULL;
    size_t in_len = 0, in_cap = 0, in_pos = 0;
    int c;
    while ((c = getchar()) != EOF) {
        if (in_len == in_cap) {
            in_cap = in_cap ? in_cap * 2 : 256;
            in = realloc(in, in_cap);
            if (!in) { fprintf(stderr, "oom\n"); return 2; }
        }
        in[in_len++] = (uint8_t)c;
    }

    /* --- execute ---------------------------------------------------- */
    uint32_t reg[NREG] = {0};
    uint32_t pc = 0;
    int zf = 0;
    unsigned long steps = 0;

    while (pc + 4 <= code_len) {
        if (++steps > STEP_LIMIT) { fprintf(stderr, "the tongue loops forever\n"); break; }

        uint8_t op  = code[pc];
        uint8_t a   = code[pc + 1];
        uint8_t b   = code[pc + 2];
        uint8_t imm = code[pc + 3];
        uint8_t ra  = a & (NREG - 1);
        uint8_t rb  = b & (NREG - 1);
        uint32_t next = pc + 4;

        switch (op) {
        case OP_HALT:  free(in); return 0;
        case OP_LOADI: reg[ra] = imm; break;
        case OP_MOV:   reg[ra] = reg[rb]; break;
        case OP_ADD:   reg[ra] = reg[ra] + reg[rb]; break;
        case OP_SUB:   reg[ra] = reg[ra] - reg[rb]; break;
        case OP_XOR:   reg[ra] = reg[ra] ^ reg[rb]; break;
        case OP_AND:   reg[ra] = reg[ra] & reg[rb]; break;
        case OP_MIX:   reg[ra] = tape[reg[ra] & 0xFF]; break;
        case OP_LOAD:  reg[ra] = tape[reg[rb] & (TAPE_SIZE - 1)]; break;
        case OP_STORE: tape[reg[ra] & (TAPE_SIZE - 1)] = reg[rb] & 0xFF; break;
        case OP_CMP:   zf = (reg[ra] == reg[rb]); break;
        case OP_JMP:   next = ((uint32_t)a << 8) | b; break;
        case OP_JZ:    if (zf)  next = ((uint32_t)a << 8) | b; break;
        case OP_JNZ:   if (!zf) next = ((uint32_t)a << 8) | b; break;
        case OP_IN:    reg[ra] = (in_pos < in_len) ? in[in_pos++] : 0; break;
        case OP_OUT:   putchar(reg[ra] & 0xFF); break;
        case OP_ROL: {
            uint32_t v = reg[ra], s = imm & 31;
            reg[ra] = s ? ((v << s) | (v >> (32 - s))) : v;
            break;
        }
        default:
            fprintf(stderr, "unknown rune 0x%02x at %u\n", op, pc);
            free(in);
            return 3;
        }
        pc = next;
    }

    free(in);
    return 0;
}
