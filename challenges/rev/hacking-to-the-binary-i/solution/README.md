# Hacking to the Binary I

**Category:** Rev  
**Difficulty:** Easy
**Author:** Grace

## Description

I ran some experiments recently and got bucket-loads of data. I made a little data organizer
software a long time ago, but for some reason I password-protected it. Of course, I've forgotten the
password now. Can you try to crack it and see what the password was?

## Files Provided

- `gedo` - Grace's Experimental Data Organizer

## Tools Used

- Ghidra
- Python

## Flag

`flag{my_homemade_hash_sux}`

## Solution

If we run the binary we see
```
$ ./gedo
Grace's Experimental Data Organizer

+-------------------------------------+
|                                     |
|       |\      _,,,---,,_            |
| ZZZzz /,`.-'`'    -.  ;-;;,_        |
|      |,4-  ) )-,_. ,\ (  `'-'       |
|     '---''(_/--'  `-'\_)  Felix Lee |
|                                     |
+-------------------------------------+

Enter Password:
```
So we must somehow get a password to get the flag. Also, peep the awesome ascii art. Putting it
straight to Ghidra, we get the decompilation
```c
undefined8 main(void) {
  long lVar1;
  long in_FS_OFFSET;
  undefined8 local_38;
  undefined2 local_30;
  undefined2 uStack_2e;
  undefined2 uStack_2c;
  undefined2 uStack_2a;
  undefined2 local_28;
  undefined2 local_26;
  undefined8 local_24;
  long local_10;
  
  local_10 = *(long *)(in_FS_OFFSET + 0x28);
  printf("%s",ascii_art);
  local_38 = 0;
  // ...
  local_24 = 0;
  printf("Enter Password: ");
  fgets((char *)&local_38,0x1c,stdin);
  lVar1 = xorhash((undefined2)local_38);
  if (lVar1 == -0x1b4cd19eaf449022) {
    flag = (byte)local_38 ^ flag;
    DAT_00104011 = local_38._1_1_ ^ DAT_00104011;
  }
...
}
```

Notice that `local_38` is where the input is being placed since it's the first argument off
`fgets()`. `fgets()` is reading 28 bytes, so we can maybe assume that `local_38` is an array 28
bytes long. We can then retype `local_38` to `unsigned char[28]`, and we get
```c
undefined8 main(void) {
  long lVar1;
  long lVar2;
  long in_FS_OFFSET;
  char local_38 [28];
  
  lVar1 = *(long *)(in_FS_OFFSET + 0x28);
  printf("%s",ascii_art);
  local_38[0] = '\0';
  // ...
  local_38[0x1b] = '\0';
  printf("Enter Password: ");
  fgets(local_38,0x1c,stdin);
  lVar2 = xorhash(local_38._0_2_);
  if (lVar2 == -0x1b4cd19eaf449022) {
    flag = local_38[0] ^ flag;
    DAT_00104011 = local_38[1] ^ DAT_00104011;
  }
  ...
}
```

Next, we see a bunch of repetition.
```c
undefined8 main(void) {
  ...
  lVar2 = xorhash(local_38._0_2_);
  if (lVar2 == -0x1b4cd19eaf449022) {
    flag = local_38[0] ^ flag;
    DAT_00104011 = local_38[1] ^ DAT_00104011;
  }
  ...
  lVar2 = xorhash(local_38._24_2_);
  if (lVar2 == -0x79744b5a5368ef89) {
    DAT_00104028 = local_38[0x18] ^ DAT_00104028;
    DAT_00104029 = local_38[0x19] ^ DAT_00104029;
  }
  puts((char *)&flag);
}
```

If we go to `flag`, we see that it points to somewhere in memory and it is followed by a bunch of
`DAT_` labels. Since `flag` gets printed at the end, we can assume that `flag` is a string. It has a
length of 27 based on the last part being at address `00104029` and `flag` being at address
`00104010`. So we can tell Ghidra to interpret it as a `char[27]`.
```c
  ...
  lVar2 = xorhash(local_38._0_2_);
  if (lVar2 == -0x1b4cd19eaf449022) {
    flag[0] = local_38[0] ^ flag[0];
    flag[1] = local_38[1] ^ flag[1];
  }
  ...
  lVar2 = xorhash(local_38._24_2_);
  if (lVar2 == -0x79744b5a5368ef89) {
    flag[0x18] = local_38[0x18] ^ flag[0x18];
    flag[0x19] = local_38[0x19] ^ flag[0x19];
  }
```

The `xorhash()` function seems important, so let's look at it.
```c
ulong xorshift(ulong param_1)

{
  param_1 = param_1 ^ param_1 << 0xd;
  param_1 = param_1 ^ param_1 >> 7;
  return param_1 ^ param_1 << 0xf;
}

long xorhash(ushort param_1) {
  undefined4 local_14;
  undefined8 local_10;
  
  local_10 = (long)(int)(param_1 + 0xbeef);
  for (local_14 = 0; local_14 < 0x10; local_14 = local_14 + 1) {
    local_10 = xorshift(local_10);
  }
  return local_10;
}
```

It's just doing a bunch of bitshifting and xoring a bunch of times. Notice that `xorshift()` returns
a `ulong` and `xorhash()` doesn't really care about the signedness of what it returns. So we can
change the return type to `ulong`. We can then reimplement it in Python where it's all unsigned.
```py
def xorshift(x: int):
    x ^= x << 13;
    x &= 0xFFFFFFFFFFFFFFFF

    x ^= x >> 7;
    x &= 0xFFFFFFFFFFFFFFFF

    x ^= x << 15;
    x &= 0xFFFFFFFFFFFFFFFF

    return x

def xorhash(initial_state: int):
    state = (initial_state & 0xFFFF) + 0xBEEF
    for _ in range(16):
        state = xorshift(state)

    return state
```

Returning to the main function, let's try to understand what each blocl of repetition does. After
retyping `xorhash()` to return a `ulong`, we see that each block is now
```c
  uVar2 = xorhash(local_38._0_2_);
  if (uVar2 == 0xe4b32e6150bb6fde) {
    *flag = local_38[0] ^ *flag;
    flag[1] = local_38[1] ^ flag[1];
  }
```

It is calling `xorhash()` on `local_38._0_2_` and comparing it to a constant. If the result of
`xorhash()` matches the constant, it does some xoring on a variable named `flag` using values in
`local_38`. The interesting part is the `local_38._0_2_`. We know that `xorhash()` takes in a
`ushort` which is 2 bytes in length. We can guess `local_38._0_2_` is a `ushort` and the `._0_2_`
indicates that it is accessing 2 bytes of `local_38` at byte offset 0. This is supported by the fac
that the next block of repetition is
```c
  uVar2 = xorhash(local_38._2_2_);
  if (uVar2 == 0x6d0a99d34868bac6) {
    flag[2] = local_38[2] ^ flag[2];
    flag[3] = local_38[3] ^ flag[3];
  }
```

which moves on to the next two bytes of `local_38`. So, we just need to find the correct input so
that for each 2-byte wide chunks of `local_38` matches its corresponding constant when `xorhash()`
is called. Since `xorhash()` only takes in a `ushort`, we can just brute-force all numbers and
create a map for which hash result goes to which input. We can implement this in Python:
```py
mem = {}
for n in range(2**16):
    H = xorhash(n)
    assert H not in mem
    mem[H] = n

flag = list(b'\x15\x0f\x08\x02\x15\x19\x10\x2c\x1c\x1c\x32\x17\x08\x17\x01\x04\x33\x37\x15\x1b\x0d\x00\x15\x19\x19\x1a')

checks = [0xe4b32e6150bb6fde, 0x6d0a99d34868bac6, 0x8fbecef0ef654aec, 0x6fe2381f446a074b, 0x5f2a203f1cab029d, 0x9cac2cfa67ca4b47, 0xce13f87c924db6f0, 0xf52d7f264fadaa96, 0x3ff0a518df37dd6e, 0x6414a765c14b1efb, 0x28ac48849cc4e36e, 0xda1dc182a6cc8cad, 0x868bb4a5ac971077]

inpt = []
for i, check in enumerate(checks):
    n = mem[check]
    inpt += [(n >> 0) & 0xFF, (n >> 8) & 0xFF]
    flag[2*i  ] ^= (n >> 0) & 0xFF
    flag[2*i+1] ^= (n >> 8) & 0xFF

print(f'input: {''.join(chr(c) for c in inpt)}')
print(f'flag:  {''.join(chr(c) for c in flag)}')
```

If we run it we get:
```
input: scientists_reveal_the_flag
flag:  flag{my_homemade_hash_sux}
```

which we can verify that this is correct when we test it on the binary:
```
$ ./gedo
Grace's Experimental Data Organizer

+-------------------------------------+
|                                     |
|       |\      _,,,---,,_            |
| ZZZzz /,`.-'`'    -.  ;-;;,_        |
|      |,4-  ) )-,_. ,\ (  `'-'       |
|     '---''(_/--'  `-'\_)  Felix Lee |
|                                     |
+-------------------------------------+

Enter Password: scientists_reveal_the_flag
flag{my_homemade_hash_sux}
```

## Solve Script
Run `solve.py`

## Techniques / Tags

- `reverse-engineering`
- `caching`
- `brute-force`

## Setup / Deployment Notes

N/A

## Known Issues / Notes

N/A

