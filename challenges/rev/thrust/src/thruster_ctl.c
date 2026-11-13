// THRUST - Captain, we stopped
//
// Player-facing firmware. Build with src/build.sh (no-pie, -O0, symbols kept).
// Usage: ./thruster_ctl <authorization_code>
#include <stdio.h>
#include <string.h>

#define CODE_LEN 16
#define FLAG_LEN 30

static const unsigned char target[CODE_LEN] = {
    0x00, 0x17, 0x10, 0x0c, 0x1d, 0x2f, 0x2b, 0x21,
    0x30, 0x2d, 0x20, 0x2d, 0x36, 0x1d, 0x75, 0x63
};

static const unsigned char hidden[FLAG_LEN] = {

    0x24, 0x2e, 0x23, 0x25, 0x39, 0x32, 0x2d, 0x35,
    0x27, 0x30, 0x1d, 0x2d, 0x2c, 0x1d, 0x2e, 0x27,
    0x36, 0x31, 0x1d, 0x25, 0x2d, 0x3f, 0x42, 0x42,
    0x42, 0x42, 0x42, 0x42, 0x42, 0x42
};

static void print_flag(void) {
    char out[FLAG_LEN + 1];
    for (int i = 0; i < FLAG_LEN; i++) {
        out[i] = (char)(hidden[i] ^ 0x42);
    }
    out[FLAG_LEN] = '\0';
    puts("Authorization accepted.");
    puts(out);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        printf("Usage: %s <authorization_code>\n", argv[0]);
        return 1;
    }
    const char *input = argv[1];
    if (strlen(input) != CODE_LEN) {
        puts("Microbot guard: length mismatch.");
        return 1;
    }
    for (int i = 0; i < CODE_LEN; i++) {
        if (((unsigned char)input[i] ^ 0x42) != target[i]) {
            puts("Microbot guard: authorization rejected.");
            return 1;
        }
    }
    print_flag();
    return 0;
}
