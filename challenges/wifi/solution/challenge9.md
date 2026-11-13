# RazorVault

**Category:** WiFi
**Difficulty:** Insane
**Author:** Lt. Rico Kopernicus

## Description

There's a WPA3-protected network called RazorVault on the Icarus. Sounds like
somebody really wanted to keep people out of whatever's on the network. Find a
way to get the password.

## Flag

`flag{winterfalcon}`

## Solution

1. The players would have to find a WPA3 cracking tool to use against this AP.  The intended one
   is [Wacker](https://github.com/blunderbuss-wctf/wacker) by blunderbuss-wctf and is given in the
   hint for 100 points.
2. Follow the instructions in Wacker's README (clone the repo, build the modded wpa_supplicant, then
   run wacker)
3. The hard part is really just figuring out what they need, finding a tool, and learning how to install
   and use it from the ground up.
4. Using the included wordlist rockyou.txt, they can crack the network and get the password (winterfalcon).
 