# Grace's SHA256 Hash Collision Project

**Category:** Rev  
**Difficulty:** Medium  
**Author:** Grace

## Description

I recently found this old website I made when I was trying to break SHA256 by finding a hash
collision. It's a lot harder than I thought... maybe you can take a crack at it! If you can break
SHA256, then maybe you can bypass some of ICARUS's security systems. I think I also hid a little
reward somewhere.

Connect to `http://<URL>`

## Tools Used

- [`wasm2c`](https://github.com/WebAssembly/wabt)

## Flag

`flag{wh4t_th3_h3ck_i5_w3b4ss3mb1y}`

## Solution

Checking out the website's JS scripts, we see a short file named `index.js`

```javascript
import init, { check_hash } from "./pkg/wasm.js";
import { set } from "./helper.js"
await init()

document.getElementById("check-input").addEventListener("click", () => {
    const txt = document.getElementById("text-input").value;
    if (!txt) {
        set("The input is empty!")
        return;
    }
    check_hash(txt);
});
```

The `check_hash` function seems to be the important part. It comes from `./pkg/wasm.js`, so it's
probably a [WebAssembly](https://en.wikipedia.org/wiki/WebAssembly) function. If we download the
`.wasm` file, we get a binary version of it. We can make it human readable by using
[`wasm2c`](https://github.com/WebAssembly/wabt) and we et a huge C file. If we search through the
file looking for `check_hash` we'll find 

```c
void w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Acheck_hash(w2c_* instance, u32 var_p0, u32 var_p1) {
  u32 var_l2 = 0, var_l3 = 0, var_l4 = 0, var_l5 = 0, var_l6 = 0, var_l7 = 0, var_l8 = 0, var_l9 = 0, 
      var_l10 = 0;
  FUNC_PROLOGUE;
  ...

  goto var_B0;
  var_B2:;
  w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Aprint_flag(instance);
  goto var_B0;
  var_B1:;
  ...
}
```

If we scroll around the function a little, we can see a function called
`w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Aprint_flag`!!! print_flag!!! If we go to the function
definition we'll see something like

```c
void w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Aprint_flag(w2c_* instance) {
  u32 var_l0 = 0, var_l1 = 0, var_l2 = 0, var_l3 = 0, var_l4 = 0, var_l5 = 0, var_l6 = 0, var_l7 = 0, ...;
  FUNC_PROLOGUE;
  u32 var_i0, var_i1, var_i2, var_i3;
  u64 var_j1;
  // Part A
  var_i0 = instance->w2c_0x5F_stack_pointer;
  var_i1 = 176u;
  var_i0 -= var_i1;
  var_l0 = var_i0;
  var_i0 = var_l0;
  instance->w2c_0x5F_stack_pointer = var_i0;
  ...

  // Part B 
  var_i0 = 101u;
  var_l1 = var_i0;
  var_i0 = var_l0; // stack ptr (sp)
  var_i1 = var_l1; // 101u
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 36, var_i1); // [sp + 36] := 101u

  var_i0 = var_l0;
  var_i1 = 118u;
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 37, var_i1); // [sp + 37] := 118u
  ...
  
  // Part C
  var_i0 = var_l0;
  var_i0 = i32_load8_u_default32(&instance->w2c_memory, (u64)(var_i0) + 36u); // var_i0 := [sp + 36]
  var_i1 = var_l0;
  var_i1 = i32_load8_u_default32(&instance->w2c_memory, (u64)(var_i1) + 64u); // var_i1 := [sp + 64]
  var_i0 ^= var_i1;
  var_l16 = var_i0; // var_l16 := var_i0 ^ var_i1

  var_i0 = var_l0;
  var_i0 = i32_load8_u_default32(&instance->w2c_memory, (u64)(var_i0) + 37u); // var_i0 := [sp + 37]
  var_i1 = var_l0;                                                                                   
  var_i1 = i32_load8_u_default32(&instance->w2c_memory, (u64)(var_i1) + 65u); // var_i0 := [sp + 65]
  var_i0 ^= var_i1;
  var_l17 = var_i0; // var_l17 := var_i0 ^ var_i1
  ...

  // Part D
  var_i0 = var_l0; // sp
  var_i1 = var_l16; // [sp + 36] ^ [sp + 64]
  // [sp + 92] := var_l16 <=> [sp + 92] := [sp + 36] ^ [sp + 64]
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 92, var_i1);

  var_i0 = var_l0;
  var_i1 = var_l17; // [sp + 37] ^ [sp + 65]
  // [sp + 93] := var_l17 <=> [sp + 93] := [sp + 37] ^ [sp + 65]
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 93, var_i1);
  ...

  // Part E
  var_i0 = 28u;
  var_l44 = var_i0;
  var_i0 = var_l0;
  var_i1 = 8u;
  var_i0 += var_i1;
  var_i1 = var_l0;
  var_i2 = 92u;
  var_i1 += var_i2;
  var_i2 = var_l44;
  // <str>::from_utf8_unchecked(sp + 8u, sp + 92u, 28u)
  // <str>::from_utf8_unchecked(return addr, str ptr , len)
  w2c__0x3Cstr0x3E0x3A0x3Afrom_utf8_unchecked(instance, var_i0, var_i1, var_i2);
  ...
}
```

There's a lot of repetition in the function and other notable parts. We can split it up and go
through it one by one to understand what's going on.


In Part A,

```c
void w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Aprint_flag(w2c_* instance) {
  ...
  // Part A
  var_i0 = instance->w2c_0x5F_stack_pointer;
  var_i1 = 176u;
  var_i0 -= var_i1; // Grow down the stack by 176u
  var_l0 = var_i0;
  var_i0 = var_l0;
  instance->w2c_0x5F_stack_pointer = var_i0;
  ...
}
```

It simply grows down WASM's stack by 176 bytes. There's not much going on but it helps us build a
mental model of what's happening in WASM's memory.

In Part B,

```c
void w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Aprint_flag(w2c_* instance) {
  // Part B
  ...
  var_i0 = 101u;
  var_l1 = var_i0;
  var_i0 = var_l0; // stack ptr (sp)
  var_i1 = var_l1; // 101u
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 36, var_i1); // [sp + 36] := 101u

  var_i0 = var_l0;
  var_i1 = 118u;
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 37, var_i1); // [sp + 37] := 118u
  ...
}
```

We see a lot of `i32_store8_default32`s. If we follow the assignments for each
`i32_store8_default32` call, `var_i0` is the stack pointer and `var_i1` is the constants. So it's
storing these constants, e.g. `101u` and `118u`, to the stack. When it's storing the `101u`, notice
that it's also storing it to `var_l1` which doesn't happen with `118u`. This is because `101u` gets
stored again later:

```c
  var_i0 = var_l0;
  var_i1 = var_l1;
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 43, var_i1); // [sp + 43] := 101u
```

In Part C,

```c
void w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Aprint_flag(w2c_* instance) {
  ...
  // Part C
  var_i0 = var_l0; // sp
  var_i0 = i32_load8_u_default32(&instance->w2c_memory, (u64)(var_i0) + 36u); // var_i0 := [sp + 36]
  var_i1 = var_l0;
  var_i1 = i32_load8_u_default32(&instance->w2c_memory, (u64)(var_i1) + 64u); // var_i1 := [sp + 64]
  var_i0 ^= var_i1;
  var_l16 = var_i0; // var_l16 := var_i0 ^ var_i1

  var_i0 = var_l0;
  var_i0 = i32_load8_u_default32(&instance->w2c_memory, (u64)(var_i0) + 37u); // var_i0 := [sp + 37]
  var_i1 = var_l0;                                                                                   
  var_i1 = i32_load8_u_default32(&instance->w2c_memory, (u64)(var_i1) + 65u); // var_i0 := [sp + 65]
  var_i0 ^= var_i1;
  var_l17 = var_i0; // var_l17 := var_i0 ^ var_i1
  ...
}
```

We can see that it loads in two bytes from the stack, XORs them, and stores them in a variable.
Notably, it loads in the constants from Part B.

In Part D,

```c
void w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Aprint_flag(w2c_* instance) {
  ...
  // Part D
  var_i0 = var_l0; // sp
  var_i1 = var_l16; // [sp + 36] ^ [sp + 64]
  // [sp + 92] := var_l16 <=> [sp + 92] := [sp + 36] ^ [sp + 64]
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 92, var_i1);

  var_i0 = var_l0;
  var_i1 = var_l17; // [sp + 37] ^ [sp + 65]
  // [sp + 93] := var_l17 <=> [sp + 93] := [sp + 37] ^ [sp + 65]
  i32_store8_default32(&instance->w2c_memory, (u64)(var_i0) + 93, var_i1);
  ...
}
```

It simply takes the XOR results stored in variables from Part C and stores those back to the stack.

In Part E,

```c
void w2c__wasm0x5B4d9c9e1f924520420x5D0x3A0x3Aprint_flag(w2c_* instance) {
  ...
  // Part E
  var_i0 = 28u;
  var_l44 = var_i0;
  var_i0 = var_l0;
  var_i1 = 8u;
  var_i0 += var_i1;
  var_i1 = var_l0;
  var_i2 = 92u;
  var_i1 += var_i2;
  var_i2 = var_l44;
  // <str>::from_utf8_unchecked(sp + 8u, sp + 92u, 28u)
  // <str>::from_utf8_unchecked(return addr, str ptr , len)
  w2c__0x3Cstr0x3E0x3A0x3Afrom_utf8_unchecked(instance, var_i0, var_i1, var_i2);
  ...
}
```

We can see that it calls some function with a weird name that contains `str` and
`from_utf8_unchecked`. If you realize that the hex decimals are ASCII and the proper method name is
`<str>::from_utf8_unchecked`. Looking that up, we can see that it's a rust function that takes a
slice of `u8`s, `&[u8]`, and transforms it into a string slice, `&str`. By following the
assignments, we can see that `var_i1 := sp + 92u` and `var_i2 := 28u`.

Notice that `sp + 92u` is where Part D started and there were exactly 28 `i32_store8_default32`
calls. We can assume that `var_i1` is being treates as a pointer to an array and `var_i2` is the
length of the array. This is further supported by the fact that a slice in Rust is made up of a
pointer to an array and the length of the array.

It's not totally clear what `var_i0 := sp + u8` is used for, but If we look at the internals of the
`<str>::from_utf8_unchecked` in WASM, it's used as a pointer to the stack and things are being
stored there. So, we can assume that the result of the call is stored in the stack in `var_i0 = sp +
8u`. But that's not really important. It's enough to know that the function is creating a string.

In summary, it's loading a bunch of constants to memory, XORing those constants, putting them back
in memory, and turning them into a string. So all we need to do is extract those constants, XOR the
proper constants, and turn it into a string. If we do that, we get the string
`wh4t_th3_h3ck_i5_w3b4ss3mb1y` and we can turn it into the flag format
`flag{wh4t_th3_h3ck_i5_w3b4ss3mb1y}`.

## Solve Script

Run `solve.py`.

## Techniques / Tags

`web-assembly`; `reverse-engineering`

## Setup / Deployment Notes

Run `docker compose up` in the parent folder, then connect to `http://localhost`

## Known Issues / Notes

N/A
