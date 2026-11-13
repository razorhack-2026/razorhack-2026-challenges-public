## Challenge Solution for Brailliant Minds  


**Author:** Mort (StevieoXOR)  
**Category:** Rev (Reverse Engineering)  
**Difficulty:** medium  

### ChallengeDescription_Themed_ViewableByParticipant  
A stream of seemingly encoded data was intercepted from a known associate of Dr. Rootkit. The threat detection team used the data's embedded newline characters as a delimiter, forming ostensibly rectangular regions in the encoded text. Can you further decipher the message?  

### Required Tools  
* https://text2braille.com  
* Squinting is (probably) necessary but not sufficient.  

### Overall Goal  
Cipher: Interpret text as a noisy bitmap by converting the provided text to Braille, and then (maybe squinting) to read regular English characters.  

### Valid Flags  
- flag{braille}  
- flag{BRAILLE}  
- FLAG{braille}  
- FLAG{BRAILLE}  

### Notes  
* CyberChef could theoretically help, but it likely won't help you here due to its UTF-8 encodings not working properly.  
  * `Brute Force Text Decode` correctly displays Braille characters while UTF-8 encode/decode doesn't.  

* The "Debug" section at the top is to hint at a possible set of character mappings that might be useful for the challenge.  
  * When this "Debug" section is provided, Gemini 3.1 Pro solved it in slightly under 5 minutes (with a decent system prompt about CoT reasoning and logic) with a user prompt that said "Solve this challenge. Maybe it has the word "flag" in it?".  

* The "Checksum" section is not important to solving the challenge at all.  







### Appendix - LLM Answers

Gemini 3.1 Pro with the Debug text at the top:
"""
The solution to the challenge is the flag **FLAG{BRAILLE}**.

The file "BrailliantMinds.txt" encodes a hidden message using an ASCII-art substitution cipher based on the Braille alphabet. The 5-line text blocks are not random; they form large letters when you map the characters to "filled" or "empty" pixels based on their corresponding Braille dot density.

By substituting "heavy" Braille characters (e.g., `q`, `g`, `l`, `p`, `t`) with a solid block like `#` and "light" characters (e.g., `a`, `i`, `u`, `e`) with empty space `.`, the text visually renders individual characters separated by delimiters like `Alla` or `ALa`.

Here is how the first block decodes into the letters **F L A**:

**F**

```text
qggggg -> ######
qauiii -> #.....
qggqii -> ####..
qauiui -> #.#.#.
qaiiii -> #.....

```

**L**

```text
qiuee -> #....
piuii -> #....
pauuu -> #....
qaiii -> #....
qgggq -> #####

```

**A**

```text
iggge -> .###.
quiuq -> #...#
)qgq( -> .###. 
guiug -> #...#
giuig -> #...#

```

Mapping this technique across all the blocks reveals the entire flag in sequence:

* **Block 1:** `F L A`
* **Block 2:** `G {`
* **Block 3:** `B R A`
* **Block 4:** `I L`
* **Block 5:** `L E`
* **Block 6:** `}`

The "DEBUG" grid provided at the top serves as the cipher's character map, laying out the standard Braille ASCII character set in sequential order, dictating which characters represent dark or light pixels.
"""






Gemini 3.1 Pro, in a new chat, with the Debug removed, and another checksum that is equivalent (but named Starting Checksum, and the latter renamed to Ending Checksum) placed at the top of the file:  

Solved in 2 minutes and 45 seconds.  

User's prompt:  
"""
@use-braincells Solve this challenge. Maybe it has the word "flag" in it?
"""

"""
```python
import os

if os.path.exists("BrailliantMinds.txt"):
    with open("BrailliantMinds.txt", "r") as f:
        print(f.read()[:500])
else:
    print("File not found.")


```

```text
Starting Checksum
/ggqqAlla#(())ll;/qggqea
qaaaaA-%-U*_lal:qaaaeqa
qqgg!A-'-::'::al;qaaaaaa
qa*aqammaAddrzal:qaaa)qa
\qgqaA__aeafhrhl;\gggqa


qgggggallaqiueeAllaiggge
qauiiiallapiuiiAllaquiuq
qggqiiallapauuuAlla)qgq(
qauiuiallaqaiiiAllaguiug
qaiiiiallaqgggqAllagiuig

qgggggAllaaatttAlla
qA0.AllaattaAalla
qAwwwAllawlaaAalla
q-+9qAllaattaAalla
egggggAllaaatttAlla

qggqaAllaqggqaALaigggea
qaaaqALaqaaalALaguXga
qggg!AllaqggqaALaqgqgqa
qa*aqaLaaqaalaALaquiuqa
qqqqaAllaqaalaALaqiuiqa

qqqqqAL;aqvaaee


```

```python
with open("BrailliantMinds.txt", "r") as f:
    lines = f.read().splitlines()

for i, line in enumerate(lines):
    print(f"{i:02d}: {line}")


```

```text
00: Starting Checksum
01: /ggqqAlla#(())ll;/qggqea
02: qaaaaA-%-U*_lal:qaaaeqa
03: qqgg!A-'-::'::al;qaaaaaa
04: qa*aqammaAddrzal:qaaa)qa
05: \qgqaA__aeafhrhl;\gggqa
06: 
07: 
08: qgggggallaqiueeAllaiggge
09: qauiiiallapiuiiAllaquiuq
10: qggqiiallapauuuAlla)qgq(
11: qauiuiallaqaiiiAllaguiug
12: qaiiiiallaqgggqAllagiuig
13: 
14: qgggggAllaaatttAlla
15: qA0.AllaattaAalla
16: qAwwwAllawlaaAalla
17: q-+9qAllaattaAalla
18: egggggAllaaatttAlla
19: 
20: qggqaAllaqggqaALaigggea
21: qaaaqALaqaaalALaguXga
22: qggg!AllaqggqaALaqgqgqa
23: qa*aqaLaaqaalaALaquiuqa
24: qqqqaAllaqaalaALaqiuiqa
25: 
26: qqqqqAL;aqvaaee
27: eaqaaALaayyaaee
28: eeleaALlaqqeeaa
29: e_g_aAL;avveeaa
30: qgggqALaaqggqvv
31: 
32: AL;aqqaaeeAL;aq7a7
33: ALaayqaaeeAllaayqaaee
34: ALlaqyeeaaALlaqg77
35: AL;ayqeeaaAll;ayqeeaa
36: ALaaqyqqqqALaaqyqqqq
37: 
38: ALaaczzea/ea
39: Allaaaazzzaaa
40: AL;aaaalqraa
41: Allaaaaattaea
42: ALaa_*ttAia
43: Anorstyznorst
44: 
45: 
46: Ending Checksum
47: /ggqqAlla#(())ll;/qggqea
48: qaaaaA-%-U*_lal:qaaaeqa
49: qqgg!A-'-::'::al;qaaaaaa
50: qa*aqammaAddrzal:qaaa)qa
51: \qgqaA__aeafhrhl;\gggqa


```

```python
with open("BrailliantMinds.txt", "r") as f:
    lines = f.read().splitlines()

for i, line in enumerate(lines):
    if line.strip() and not line.startswith("Starting") and not line.startswith("Ending"):
        print(f"{i:02d}: len={len(line)} {line}")


```

```text
01: len=24 /ggqqAlla#(())ll;/qggqea
02: len=23 qaaaaA-%-U*_lal:qaaaeqa
03: len=24 qqgg!A-'-::'::al;qaaaaaa
04: len=24 qa*aqammaAddrzal:qaaa)qa
05: len=23 \qgqaA__aeafhrhl;\gggqa
08: len=24 qgggggallaqiueeAllaiggge
09: len=24 qauiiiallapiuiiAllaquiuq
10: len=24 qggqiiallapauuuAlla)qgq(
11: len=24 qauiuiallaqaiiiAllaguiug
12: len=24 qaiiiiallaqgggqAllagiuig
14: len=19 qgggggAllaaatttAlla
15: len=17 qA0.AllaattaAalla
16: len=18 qAwwwAllawlaaAalla
17: len=18 q-+9qAllaattaAalla
18: len=19 egggggAllaaatttAlla
20: len=23 qggqaAllaqggqaALaigggea
21: len=21 qaaaqALaqaaalALaguXga
22: len=23 qggg!AllaqggqaALaqgqgqa
23: len=23 qa*aqaLaaqaalaALaquiuqa
24: len=23 qqqqaAllaqaalaALaqiuiqa
26: len=15 qqqqqAL;aqvaaee
27: len=15 eaqaaALaayyaaee
28: len=15 eeleaALlaqqeeaa
29: len=15 e_g_aAL;avveeaa
30: len=15 qgggqALaaqggqvv
32: len=18 AL;aqqaaeeAL;aq7a7
33: len=21 ALaayqaaeeAllaayqaaee
34: len=18 ALlaqyeeaaALlaqg77
35: len=21 AL;ayqeeaaAll;ayqeeaa
36: len=20 ALaaqyqqqqALaaqyqqqq
38: len=12 ALaaczzea/ea
39: len=13 Allaaaazzzaaa
40: len=12 AL;aaaalqraa
41: len=13 Allaaaaattaea
42: len=11 ALaa_*ttAia
43: len=13 Anorstyznorst
47: len=24 /ggqqAlla#(())ll;/qggqea
48: len=23 qaaaaA-%-U*_lal:qaaaeqa
49: len=24 qqgg!A-'-::'::al;qaaaaaa
50: len=24 qa*aqammaAddrzal:qaaa)qa
51: len=23 \qgqaA__aeafhrhl;\gggqa


```

```python
with open("BrailliantMinds.txt", "r") as f:
    text = f.read()

import string
unique_chars = set(text)
print(sorted(unique_chars))


```

```text
['\n', ' ', '!', '#', '%', "'", '(', ')', '*', '+', '-', '.', '/', '0', '7', '9', ':', ';', 'A', 'C', 'E', 'L', 'S', 'U', 'X', '\\', '_', 'a', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'y', 'z']


```

The text in `BrailliantMinds.txt` is an ASCII art puzzle where characters function as individual pixels to form larger letters.

By analyzing the structure, the text is broken into a "Starting Checksum", six distinct blocks of text, and an "Ending Checksum". The core logic for decoding the puzzle lies in observing the repeating substrings (like `Alla`, `ALa`, `All`, `AL;`, and `ALla`), which act as **column delimiters**. The characters between these delimiters act as pixels: heavily weighted characters (like `q`, `g`, `p`) represent filled blocks, while lighter characters, vowels, and punctuation (like `a`, `i`, `u`, `e`) represent empty spaces.

Here is the step-by-step logical extraction of each block:

### Block 1 (Lines 8-12)

Splitting the first block by its `alla`/`Alla` delimiters yields three columns. Mapping the characters to filled (`#`) and empty (` `) spaces reveals the first three letters:

* **Column 1:** `qggggg`, `qauiii`, `qggqii`, `qauiui`, `qaiiii` forms **F**
* **Column 2:** `qiuee`, `piuii`, `pauuu`, `qaiii`, `qgggq` forms **L**
* **Column 3:** `iggge`, `quiuq`, `)qgq(`, `guiug`, `giuig` forms **A**

### Block 2 (Lines 14-18)

Using the same `Alla`/`All` delimiters:

* **Column 1:** `qggggg`, `qA0.`, `qAwww`, `q-+9q`, `eggggg` forms **G**
* **Column 2:** `aaattt`, `aattaA`, `awlaaA`, `aattaA`, `aaattt` forms **{**

### Block 3 (Lines 20-24)

* **Column 1:** `qggqa`, `qaaaq`, `qggg!`, `qa*aq`, `qqqqa` forms **B**
* **Column 2:** `qggqa`, `qaaal`, `qggqa`, `qaala`, `qaala` forms **R**
* **Column 3:** `igggea`, `guXga`, `qgqgqa`, `quiuqa`, `qiuiqa` forms **A**

### Block 4 (Lines 26-30)

* **Column 1:** `qqqqq`, `eaqaa`, `eelea`, `e_g_a`, `qgggq` forms **I**
* **Column 2:** `aqvaaee`, `ayyaaee`, `aqqeeaa`, `avveeaa`, `aqggqvv` forms **L**

### Block 5 (Lines 32-36)

* **Column 1:** `aqqaaee`, `ayqaaee`, `aqyeeaa`, `ayqeeaa`, `aqyqqqq` forms **L**
* **Column 2:** `aq7a7`, `aayqaaee`, `aqg77`, `;ayqeeaa`, `aqyqqqq` forms **E**

### Block 6 (Lines 38-42)

This final block contains only one column before tailing off with an unformatted artifact string (`Anorstyznorst`):

* **Column 1:** `aczzea/ea`, `aaaazzzaaa`, `aaaalqraa`, `aaaaattaea`, `a_*ttAia` forms **}**

Piecing the extracted columns together sequentially yields `F L A G { B R A I L L E }`.

The flag is **FLAG{BRAILLE}**.
"""



