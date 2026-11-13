
# Challenge Solution: Directional Slopes

## Overview  
**Challenge Name:**  Directional Slopes  
**Category:**   Sheet Music / Steganography  
**Difficulty:** medium  
**Author:**     Mort  
**Flag:**       flag{sl0p3s_N_D3r1v4t1v3s_R_Gr4T3!}  



## TL;DR

Slope of adjacent pitches indicates 0 or 1.
* Ex: C,E,F,G (all in same octave) == 1.  G,E,C (all in same octave) == 0.

After getting 0s and 1s, convert to 8-bits-per-char ASCII.


## Step-by-Step Solution

1.
File & Context Analysis  

The provided files consist of:  
* DirectionalSlopes_4ppb_7div_Noise.ly (LilyPond source notation)  
* DirectionalSlopes_4ppb_7div_Noise.pdf (Rendered-visible sheet music)  
* DirectionalSlopes_4ppb_7div_Noise.mid (MIDI file)  

### Key hints embedded in the file metadata and setup:  

Filename (4ppb_7div):  
* Hints at 4 pitches per block (4ppb) and 7 octave divisions / diatonic pitch scale degrees (7div, corresponding to notes $c', d', e', f', g', a', b', c''$).  

Title ("Directional Slopes"):  
* Refers to the pitch trend / slope direction of notes in each measure block (i.e., whether pitch values are non-decreasing / upward or non-increasing / downward).  

Structure:  
* The music score is divided into 37 numbered sections (#0 through #36).  
* Each section contains 8 blocks of 4 notes each (a total of 296 blocks of 4 notes).  


<br>
<br>
2.
Encoding & Decoding Scheme  

### Pitch Mapping:  

Assign each absolute diatonic pitch degree in C Major a numeric value from 0 to 7:  

<!-- LaTeX Math Block (For KaTeX/MathJax-enabled platforms like Obsidian, Jupyter, Notion) -->
<!-- $$\begin{array}{cccccccc} c' & d' & e' & f' & g' & a' & b' & c'' \\ 0 & 1 & 2 & 3 & 4 & 5 & 6 & 7 \end{array}$$   -->

<!-- Universal Markdown Table (Renders on GitHub, Notion, Discord, Reddit) -->
| c' | d' | e' | f' | g' | a' | b' | c'' |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |

### Slope / Direction Determination:  

Each block of 4 notes $(n_1, n_2, n_3, n_4)$ forms a slope:  
* UP (1): $n_1 \le n_2 \le n_3 \le n_4$ (monotonic non-decreasing)  
* DOWN (0): $n_1 \ge n_2 \ge n_3 \ge n_4$ (monotonic non-increasing)  

Bit-to-Byte Conversion:  
* Each section (#0 to #36) consists of 8 measure blocks = 8 bits = 1 byte (MSB to LSB).  
<br>

* Section #0 (00000000 / 0x00) acts as an AllZeros byte preamble.  
* Section #1 (11111111 / 0xFF) acts as a AllOnes byte preamble.  
* Sections #2 through #36 yield the ASCII payload forming the flag.  


<br>
<br>
# 3. Detailed Section-by-Section Breakdown

| Section | Pitch Block Slopes (8 Bits) | Binary Byte | Hex | ASCII Character |
| :--- | :--- | :--- | :--- | :--- |
| #0 | DOWN DOWN DOWN DOWN DOWN DOWN DOWN DOWN | 00000000 | 0x00 | All Zeros (Preamble) |
| #1 | UP UP UP UP UP UP UP UP | 11111111 | 0xFF | All Ones (Preamble) |
| #2 | DOWN UP UP DOWN DOWN UP UP DOWN | 01100110 | 0x66 | f |
| #3 | DOWN UP UP DOWN UP UP DOWN DOWN | 01101100 | 0x6C | l |
| #4 | DOWN UP UP DOWN DOWN DOWN DOWN UP | 01100001 | 0x61 | a |
| #5 | DOWN UP UP DOWN DOWN UP UP UP | 01100111 | 0x67 | g |
| #6 | DOWN UP UP UP UP DOWN UP UP | 01111011 | 0x7B | { |
| #7 | DOWN UP UP UP DOWN DOWN UP UP | 01110011 | 0x73 | s |
| #8 | DOWN UP UP DOWN UP UP DOWN DOWN | 01101100 | 0x6C | l |
| #9 | DOWN DOWN UP UP DOWN DOWN DOWN DOWN | 00110000 | 0x30 | 0 |
| #10 | DOWN UP UP UP DOWN DOWN DOWN DOWN | 01110000 | 0x70 | p |
| #11 | DOWN DOWN UP UP DOWN DOWN UP UP | 00110011 | 0x33 | 3 |
| #12 | DOWN UP UP UP DOWN DOWN UP UP | 01110011 | 0x73 | s |
| #13 | DOWN UP DOWN UP UP UP UP UP | 01011111 | 0x5F | _ |
| #14 | DOWN UP DOWN DOWN UP UP UP DOWN | 01001110 | 0x4E | N |
| #15 | DOWN UP DOWN UP UP UP UP UP | 01011111 | 0x5F | _ |
| #16 | DOWN UP DOWN DOWN DOWN UP DOWN DOWN | 01000100 | 0x44 | D |
| #17 | DOWN DOWN UP UP DOWN DOWN UP UP | 00110011 | 0x33 | 3 |
| #18 | DOWN UP UP UP DOWN DOWN UP DOWN | 01110010 | 0x72 | r |
| #19 | DOWN DOWN UP UP DOWN DOWN DOWN UP | 00110001 | 0x31 | 1 |
| #20 | DOWN UP UP UP DOWN UP UP DOWN | 01110110 | 0x76 | v |
| #21 | DOWN DOWN UP UP DOWN UP DOWN DOWN | 00110100 | 0x34 | 4 |
| #22 | DOWN UP UP UP DOWN UP DOWN DOWN | 01110100 | 0x74 | t |
| #23 | DOWN DOWN UP UP DOWN DOWN DOWN UP | 00110001 | 0x31 | 1 |
| #24 | DOWN UP UP UP DOWN UP UP DOWN | 01110110 | 0x76 | v |
| #25 | DOWN DOWN UP UP DOWN DOWN UP UP | 00110011 | 0x33 | 3 |
| #26 | DOWN UP UP UP DOWN DOWN UP UP | 01110011 | 0x73 | s |
| #27 | DOWN UP DOWN UP UP UP UP UP | 01011111 | 0x5F | _ |
| #28 | DOWN UP DOWN UP DOWN DOWN UP DOWN | 01010010 | 0x52 | R |
| #29 | DOWN UP DOWN UP UP UP UP UP | 01011111 | 0x5F | _ |
| #30 | DOWN UP DOWN DOWN DOWN UP UP UP | 01000111 | 0x47 | G |
| #31 | DOWN UP UP UP DOWN DOWN UP DOWN | 01110010 | 0x72 | r |
| #32 | DOWN DOWN UP UP DOWN UP DOWN DOWN | 00110100 | 0x34 | 4 |
| #33 | DOWN UP DOWN UP DOWN UP DOWN DOWN | 01010100 | 0x54 | T |
| #34 | DOWN DOWN UP UP DOWN DOWN UP UP | 00110011 | 0x33 | 3 |
| #35 | DOWN DOWN UP DOWN DOWN DOWN DOWN UP | 00100001 | 0x21 | ! |
| #36 | DOWN UP UP UP UP UP DOWN UP | 01111101 | 0x7D | } |


### Recovered Flag
Combining all decoded characters from sections #2 through #36:  
`flag{sl0p3s_N_D3r1v4t1v3s_R_Gr4T3!}`
