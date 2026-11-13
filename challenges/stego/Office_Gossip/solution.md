# Office Gossip

**Author:** Davie Bowman
**Category:** Stego
**Difficulty:** Easy

## Description

Catching you up on the office gossip since you're new here, I guess. Everyone already knows now anyway. The password to my office is "ACHTUNG" if you wanna swing by and chat. I've been lonely since MH left.

## Flag

`flag{rightpersonwrongtime}`

## Solution

1. The player is given a png file titled "pleasetalktomeagain.bmp"
2. They should put it in openstego and use the password in the description to extract the data, which is "youllneverfindanyonelikeme.txt"
3. the flag is on the .txt file, which is flag{rightpersonwrongtime}
