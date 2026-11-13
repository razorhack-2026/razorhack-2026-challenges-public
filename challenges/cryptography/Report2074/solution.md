# Report2074

**Category:** Cryptography
**Difficulty:** Easy
**Author:** Davie Bowman

## Description (what the competitor will see)

Being the new guy here means taking on the boring work. We get these weird reports from an unknown sender every one in awhile, and they're usually a lot of gibberish, but you never know!

## Files Provided

- Report2074.txt

## Flag

`flag{great_holes_secretly_are_digged_where_earths_pores_ought_to_suffice_and_things_have_learned_to_walk_that_ought_to_crawl}`

## Solution

1. Player will download and look at Report2074.txt
2. There is a small piece of writing at the bottom of the file, this is a hint. But, there is a list of pieces of writing that look similar to the "flag{...}" format, so participants will start decrypting those
3. They will find that each one is not simply decrypted. First (because of the hint at the bottom), they must mirror the inner contents of the flag, and then decrypt it
4. After flipping the inner contents, they can decrypt it with the Vigenere cipher, using the key Kalium (also referenced at the bottom of the file).
