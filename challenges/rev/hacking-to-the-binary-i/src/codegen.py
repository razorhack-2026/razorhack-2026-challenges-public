#!/usr/bin/env python3
def xorshifthash(initial_state: int):
    def f(x):
        x &= 0xFFFFFFFFFFFFFFFF

        x ^= x << 13;
        x &= 0xFFFFFFFFFFFFFFFF

        x ^= x >> 7;
        x &= 0xFFFFFFFFFFFFFFFF

        x ^= x << 15;
        x &= 0xFFFFFFFFFFFFFFFF

        return x
    
    state = initial_state
    for _ in range(16):
        state = f(state)

    return state

flag = b'flag{my_homemade_hash_sux}'
key  = b'scientists_reveal_the_flag'

flag_xor = bytes(a ^ b for a, b in zip(flag, key))
key_u16  = [int.from_bytes(key[i:i+2], byteorder='little') for i in range(0, len(key), 2)]
checks = [xorshifthash(k + 0xBEEF) for k in key_u16]

c_code = rf'''\
char* ascii_art = 
"Grace's Experimental Data Organizer\n\n"
"+-------------------------------------+\n"
"|                                     |\n"
"|       |\\      _,,,---,,_            |\n"
"| ZZZzz /,`.-'`'    -.  ;-;;,_        |\n"
"|      |,4-  ) )-,_. ,\\ (  `'-'       |\n"
"|     '---''(_/--'  `-'\\_)  Felix Lee |\n"
"|                                     |\n"
"+-------------------------------------+\n\n";
#include <stdio.h>
#include <stdint.h>

uint64_t xorshift(uint64_t x) {{
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 15;
    return x;
}}

uint64_t xorhash(uint16_t s) {{
    uint64_t state = s + 0xBEEF;
    for (int i = 0; i < 16; i++) {{
        state = xorshift(state);
    }}
    return state;
}}

char flag[] = "{''.join(f'\\x{b:02x}' for b in flag_xor)}";

int main() {{
    printf("%s", ascii_art);

    char key[{len(key)+2}] = {{0}};
    printf("Enter Password: ");
    fgets(key, {len(key)+2}, stdin);
    uint16_t *shorts = (uint16_t*)key;

    {'\n\t'.join(f'if(xorhash(shorts[{hex(i)}]) == {hex(check)}U) {{ flag[0x{2*i:02x}] ^= key[0x{2*i:02x}]; flag[0x{2*i+1:02x}] ^= key[0x{2*i+1:02x}]; }}' for i, check in enumerate(checks))}
    printf("%s\n", flag);
    return 0;
}}
'''

with open('./gedo.c', 'w') as f:
    f.write(c_code)
