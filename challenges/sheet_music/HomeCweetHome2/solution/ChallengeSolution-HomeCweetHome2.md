# CTF Challenge Solution: Home Cweet Home 2  

## Challenge Overview  
**Challenge Name:** Home Cweet Home 2  
**Creator:** Mort  
**Difficulty:** medium  
**Category:** Steganography / Sheet Music  

**ChallengeDescription_Themed_ViewableByParticipant:**  
Heard by microphone recording and transcribed to sheet music by a staff member with perfect pitch, a security officer noticed that many notes gradually increased in pitch while seeming out of tune, possibly an issue with the microphone or the security team's transcriber, and that the notes after the ascent sounded like they were trying to form a song, but failing. The security officer also mentioned hearing the staff member mumbling about how he enjoyed getting to interact with microtones but that he still hated his job listening to these sounds.  

**Flags:**  
- flag{distancefromtheletterabelowmiddlec}  
- flag{DISTANCEFROMTHELETTERABELOWMIDDLEC}  
- FLAG{distancefromtheletterabelowmiddlec}  
- FLAG{DISTANCEFROMTHELETTERABELOWMIDDLEC}  

**Files:**  
- dist/HCH_2-Tutorial(NoFlag)-MeecroMicro.ly  
- dist/HCH_2-Tutorial(NoFlag)-MeecroMicro.mid  
- dist/HCH_2-Tutorial(NoFlag)-MeecroMicro.pdf  
- dist/HomeCweetHome2.ly  
- dist/HomeCweetHome2.pdf  
- dist/HomeCweetHome2.mid  

---

## Step 1: Noticeable Quirks About the Data

### A) Unusual File Format
- The challenge is delivered as a **LilyPond file** (.ly), a specialized markup language for music notation—uncommon in CTF challenges, which typically use images, text, or code.
- Most participants won't immediately recognize LilyPond syntax and may assume this is purely a music challenge.

### B) Indexed Comments Instead of Solely Note Names
```lilypond
% #0
a4            
% #1
aqs           
% #2
as            
% #3
atqs          

% #4
b             
% #5
bqs           
% #6
c'            
% #7
cqs'          
\break
```
Rather than relying solely on traditional note descriptions, the creator explicitly numbered each note position from #0 to #48 (49 total).  
This numbering is the **critical hint**, and is what makes it easier to write a parser script.  
* In Lilypond code, comments are single-line, and start with `%`

### C) Deliberate Message in the Subtitle
```lilypond
subtitle = "'flag' keyword is included here, but not '{' nor '}'.  The extracted word is the flag."
```
This subtitle is **not** describing the visual appearance. Instead, it's telling you:
- A word called "flag" exists in the data
- It's not surrounded by curly braces `{}`
- Everything after "flag" is the actual flag

### D) Documented Encoding Process (Hidden in Comments)
Lines 29–33 reveal the transformation pipeline:
```
Secret string → list(EnglishLetter) → LetterToNumber → FindOctvDivisionScale 
→ ToRelativeMusicNotePitch → ToAbsoluteMusicNotePitch → AddMusicMetadata
```
This is an **explicit roadmap** showing that the encoding reverses: Note → Pitch → Number → Letter.

### E) Octave Variation Beyond Simple Chromatic Scale
The notes use different octaves: `c'`, `c''`, `c'''` (in the Lilycode, indicated by apostrophes and sometimes commas).  
While pitches at comments #0–#25 show a clear chromatic pattern across octaves, the remaining pitches (indicated by comment `% #26` and onward) get reused (e.g., `atqs'` appears at both #59 and #60).  
**This is intentional:** the indexed position matters, not whether each pitch is unique.

---

## Step 2: The Key Insight or Technique

### Core Principle: Direct Index-to-Letter Mapping

The solution relies on a **lookup table** where the comment index maps directly to a "note name"/"pitch", that, once decoded, becomes a letter of the English alphabet:
The pitch that is right below each index label is a single English letter from A–Z, but the letter is encoded via 24-TET chromatic scale, across more than one octave.

```
Index 0–25 = Definition Phase (English letters A–Z, in order, but encoded by 24-TET chromatic scale across octaves)
Index 26–... = Encoded Message (currently unknown, but encoded by 24-TET chromatic scale across octaves)
```

### The Lookup Table (Indexes 0–25)

These first 26 notes establish the cipher:

| Index | Note  | Letter | | Index | Note  | Letter |
|-------|-------|--------|-|-------|-------|--------|
| 0     | a     | A      | | 13    | dtqs' | N      |
| 1     | aqs   | B      | | 14    | e'    | O      |
| 2     | as    | C      | | 15    | eqs'  | P      |
| 3     | atqs  | D      | | 16    | f'    | Q      |
| 4     | b     | E      | | 17    | fqs'  | R      |
| 5     | bqs   | F      | | 18    | fs'   | S      |
| 6     | c'    | G      | | 19    | ftqs' | T      |
| 7     | cqs'  | H      | | 20    | g'    | U      |
| 8     | cs'   | I      | | 21    | gqs'  | V      |
| 9     | ctqs' | J      | | 22    | gs'   | W      |
| 10    | d'    | K      | | 23    | gtqs' | X      |
| 11    | dqs'  | L      | | 24    | a'    | Y      |
| 12    | ds'   | M      | | 25    | aqs'  | Z      |

**Memorize this table or save it for reference.**


## Music Knowledge Required

### Why This Table's Mapping (PitchName->EnglishLetter) Works

- **Chromatic completeness:** The 24-tone chromatic scale repeats across two octaves ([No ' nor ,], '), yielding 24*2=48 unique pitches — more than enough for 26 letters.
  - 24-tone chromatic scale can be written as:  
    A,A𝄱,A#,A𝄰, B,B𝄱, C,C𝄱,C#,C𝄰, D,D𝄱,D#,D𝄰, E,E𝄱, F,F𝄱,F#,F𝄰, G,G𝄱,G#,G𝄰  
	a,aqs,as,atqs, b,bqs, c,cqs,cs,ctqs, d,dqs,ds,dtqs, e,eqs, f,fqs,fs,ftqs, g,gqs,gs,gtqs  (uses only variations of sharps, no variations of flats. Lilypond \language "english")  
	a, btqf,bf,bqf,b, cqf,c, dtqf,df,dqf,d, etqf,ef,eqf,e, fqf,f, gtqf,gf,gqf,g, atqf,af,aqf (uses only variations of flats, no variations of sharps. Lilypond \language "english")  
	5+ more ways
- **Systematic ordering:** Notes 0–23 span one chromatic octave, 24–25 start spanning the next. This creates an unambiguous mapping.  
- **Non-musical participant advantage:** You don't need to *hear* the music or understand intervals; you only need to read the pitch at each index number, determine which octave the pitch is in (number of apostrophes/commas), know about the multiple ways of writing enharmonic notes (e.g., `B`/`b`/`Cb`/`cf`, `C`/`c`/`B#`/`bs`, `C𝄰`/`ctqs`/`dqf`, `E𝄱`/`eqs`/`fqf`/`F𝄬`), and which notes are typically included in 24TET (sharps vs flats vs both, various ways to write sharps and flats like `s`/`#` and `f`/`b`, quarter- and threeQuarter- variations of each of {sharps, flats}).

### Essential (To Understand the Challenge)

1. **Chromatic Scale:** The 12 semi-tones in Western music (C, C♯, D, D♯, E, F, F♯, G, G♯, A, A♯, B).
   - Participants unfamiliar with sharps (♯) should recognize that `cs` = C sharp.
   
2. **Octave Notation:** 
   - `c'` = C, but in the octave above Middle C  
	 Equivalently 6 whole tones above Middle C
     Equivalently 12 semi-tones above Middle C  
	 Equivalently 24 quarter tones (i.e., sequential pitches) above Middle C
   - `c''` = exactly two octaves above Middle C
   - `c'''` = exactly three octaves above Middle C
   - This is standard LilyPond/musical notation; unfamiliar participants must learn it or infer it.

3. **Middle C Context:** Understanding that "Middle C" refers to a specific reference pitch on the musical staff contextualizes the flag. However, solving the challenge does not *require* knowing this—it only adds elegance to the solution.

### Nice-to-Have (Not Required)

- LilyPond syntax (`\version`, `\header`, `\score`, etc.) is **irrelevant** to the solution. Participants can ignore all markup and focus solely on the indexed comments.
- Music theory concepts like intervals, clefs, or time signatures are **not tested** here. The challenge is purely steganographic.
- Ability to compile and render LilyPond is unnecessary—the `.ly` source file is sufficient.

---

### Decoding Process

1. **Find relevant indices (of pitches), using the comment lines**: Look at pitches that have an index of #26 and above, through to the end.
2. **Match each index's pitch to its corresponding English letter** using the lookup table.
3. **Concatenate the English letters** to form the flag.

---

## Step 3: How to Recover the Flag

### Method A: Manual Extraction (Fastest)

1. Open the `.ly` file in any text editor (e.g., `Notepad`, `Notepad++`, `VS Code`, `vim`'s `view`, `nano`, `LibreOffice`'s `Writer`, `Microsoft`'s `Word`).
2. Locate the line numbers containing notes #26–\<end\> (lines ~110–end).
3. Read each index from the comment:
   ```lilypond
	% #26
	bqs           
	% #27
	dqs'          

	% #28
	a             
	% #29
	c'                
   ```
4. Map to letters using the lookup table:
   - #26 → bqs  → F
   - #27 → dqs' → L
   - #28 → a    → A
   - #29 → c'   → G
   - ... and so on
5. **Result:** `FLAGDISTANCEFROMTHELETTERABELOWMIDDLEC`




### Method B: Programmatic Extraction (Scalable)

Here's a Python solution (located in `solution/solveHomeCweetHome1.py`) that parses the LilyPond file automatically (partially created via AI, fixed (a lot) by challenge creator):

```python
import re

def decode_lilypond_flag(filepath:str, DEBUG:bool):
	# """Extract and decode embedded flag from LilyPond file using English 24-TET Quarter-Tones."""

	# # Messed up enharmonics
	# """
	# | Index | Note  | Letter | | Index | Note  | Letter |
	# |-------|-------|--------|-|-------|-------|--------|
	# | 0     | a     | A      | | 13    | dqs'  | N      |
	# | 1     | aqs   | B      | | 14    | ds'   | O      |
	# | 2     | as    | C      | | 15    | dtqs' | P      |
	# | 3     | atqs  | D      | | 16    | e'    | Q      |
	# | 4     | b     | E      | | 17    | eqs'  | R      |
	# | 5     | bqs   | F      | | 18    | es'   | S      |
	# | 6     | bs    | G      | | 19    | etqs' | T      |
	# | 7     | btqs  | H      | | 20    | f'    | U      |
	# | 8     | c'    | I      | | 21    | fqs'  | V      |
	# | 9     | cqs'  | J      | | 22    | fs'   | W      |
	# | 10    | cs'   | K      | | 23    | ftqs' | X      |
	# | 11    | ctqs' | L      | | 24    | g'    | Y      |
	# | 12    | d'    | M      | | 25    | gqs'  | Z      |
	# """
	# ^^^ AI-generated. Messed up the fact that B# is equivalent to C and E# is equivalent to F. bs, btqs, etqs, es should each not exist.

	"""Extract and decode embedded flag from LilyPond file using English 24-TET Quarter-Tones (Enharmonically Correct)."""
	"""
	| Index | Note  | Letter | | Index | Note  | Letter |
	|-------|-------|--------|-|-------|-------|--------|
	| 0     | a     | A      | | 13    | dtqs' | N      |
	| 1     | aqs   | B      | | 14    | e'    | O      |
	| 2     | as    | C      | | 15    | eqs'  | P      |
	| 3     | atqs  | D      | | 16    | f'    | Q      |
	| 4     | b     | E      | | 17    | fqs'  | R      |
	| 5     | bqs   | F      | | 18    | fs'   | S      |
	| 6     | c'    | G      | | 19    | ftqs' | T      |
	| 7     | cqs'  | H      | | 20    | g'    | U      |
	| 8     | cs'   | I      | | 21    | gqs'  | V      |
	| 9     | ctqs' | J      | | 22    | gs'   | W      |
	| 10    | d'    | K      | | 23    | gtqs' | X      |
	| 11    | dqs'  | L      | | 24    | a'    | Y      |
	| 12    | ds'   | M      | | 25    | aqs'  | Z      |
	"""

	# Goal: Mapping: pitch_index (int) OR note_name (str) -> English_letter (A-Z)
	# index_to_letter = {
	#   0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F',
	#   6: 'G', 7: 'H', 8: 'I', 9: 'J', 10: 'K', 11: 'L',
	#   12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R',
	#   18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X',
	#   24: 'Y', 25: 'Z'
	# }
  

	# Intermediate Mapping 1: Index -> Note Name (apostrophes preserved)
	# 
	# Messed up enharmonics
	# Base note is "a" (no apostrophe). English (not Dutch) quarter-tone increments: natural, quarter-sharp (qs), sharp (s), three-quarter-sharp (tqs).
	# Octave boundary adds apostrophe at "c'" (Index 8).
	# index_to_note = {
	# 	0: "a",     1: "aqs",   2: "as",    3: "atqs",  
	# 	4: "b",     5: "bqs",   6: "bs",    7: "btqs",  
	# 	8: "c'",    9: "cqs'",  10: "cs'",  11: "ctqs'", 
	# 	12: "d'",   13: "dqs'", 14: "ds'",  15: "dtqs'", 
	# 	16: "e'",   17: "eqs'", 18: "es'",  19: "etqs'", 
	# 	20: "f'",   21: "fqs'", 22: "fs'",  23: "ftqs'", 
	# 	24: "g'",   25: "gqs'"
	# }
	# Corrected enharmonics
	# Base note is "a" (no apostrophe). English (not Dutch) quarter-tone increments: natural, quarter-sharp (qs), sharp (s), three-quarter-sharp (tqs).
	# Correct 24-TET scale: B and E have only natural and qs (no bs, btqs, es, etqs). Octave boundary adds apostrophe at "c'" (Index 6).
	index_to_note = {
		0: "a",     1: "aqs",   2: "as",    3: "atqs",  
		4: "b",     5: "bqs",   6: "c'",    7: "cqs'",  
		8: "cs'",   9: "ctqs'", 10: "d'",   11: "dqs'", 
		12: "ds'",  13: "dtqs'", 14: "e'",  15: "eqs'", 
		16: "f'",   17: "fqs'", 18: "fs'",  19: "ftqs'", 
		20: "g'",   21: "gqs'", 22: "gs'",  23: "gtqs'", 
		24: "a'",   25: "aqs'"
	}



	# Intermediate Mapping 2: Note Name -> English Letter
	# 
	# Messed up enharmonics
	# note_to_letter = {
	# 	"a": 'A',     "aqs": 'B',   "as": 'C',    "atqs": 'D',  
	# 	"b": 'E',     "bqs": 'F',   "bs": 'G',    "btqs": 'H',  
	# 	"c'": 'I',    "cqs'": 'J',  "cs'": 'K',   "ctqs'": 'L', 
	# 	"d'": 'M',    "dqs'": 'N',  "ds'": 'O',   "dtqs'": 'P', 
	# 	"e'": 'Q',    "eqs'": 'R',  "es'": 'S',   "etqs'": 'T', 
	# 	"f'": 'U',    "fqs'": 'V',  "fs'": 'W',   "ftqs'": 'X', 
	# 	"g'": 'Y',    "gqs'": 'Z'
	# }
	# Corrected enharmonics
	note_to_letter = {
		"a": 'A',     "aqs": 'B',   "as": 'C',    "atqs": 'D',  
		"b": 'E',     "bqs": 'F',   "c'": 'G',    "cqs'": 'H',  
		"cs'": 'I',   "ctqs'": 'J', "d'": 'K',    "dqs'": 'L', 
		"ds'": 'M',   "dtqs'": 'N', "e'": 'O',    "eqs'": 'P', 
		"f'": 'Q',    "fqs'": 'R',  "fs'": 'S',   "ftqs'": 'T', 
		"g'": 'U',    "gqs'": 'V',  "gs'": 'W',   "gtqs'": 'X', 
		"a'": 'Y',    "aqs'": 'Z'
	}

	def get_note_from_index(index: int) -> str:
		"""Returns pitch string with apostrophes intact."""
		# return index_to_note.get(index, "[BAD_NOTE]")
		return index_to_note.get(index, "`")

	def get_letter_from_note(note: str) -> str:
		"""Returns English letter corresponding to pitch string."""
		return note_to_letter.get(note, "~")

	def index_to_letter_chained(index: int) -> str:
		"""Chained execution: Index -> Note -> Letter."""
		note = get_note_from_index(index)
		return get_letter_from_note(note)
	
	with open(filepath, 'r') as f:
		content = f.read()
	
	# Find all lines with comment indices: % #NUMBER  (e.g., "% #0")
	#   followed by a note on the next non-empty line.
	# pattern = r'%\s*#(\d+)\s*\n\s*(\w+[\'\"]*)'	# Messes up on "a4" because "4" is part of a word (\w)
	pattern = r'%\s*#(\d+)\s*\n\s*([a-z]+[\'\"]*)'
	matches = re.findall(pattern, content)
	if DEBUG: print(matches)
	
	# Extract indices >= 26 (the encoded message)
	extracted_message, msg_after_definition = [], []
	for index_str, note in matches:
		if DEBUG: print(index_str, get_letter_from_note(note))
		msg_after_definition.append(get_letter_from_note(note))
		index = int(index_str)
		if index >= 26:  # Skip the lookup table definition pitches (0-25)
			extracted_message.append(get_letter_from_note(note))
	
	return ''.join(msg_after_definition), ''.join(extracted_message)

# Usage
LilycodeFilepath = '../dist/HomeCweetHome2.ly'  # MAY NEED TO CHANGE THIS FILEPATH
flag_strs = decode_lilypond_flag(LilycodeFilepath, DEBUG=False)
print(f"Encoded Message(s):")
[print(f"* {flag}") for flag in flag_strs]
# Expected Output:
# Encoded Message(s):
# * ABCDEFGHIJKLMNOPQRSTUVWXYZFLAGDISTANCEFROMTHELETTERABELOWMIDDLEC
# * FLAGDISTANCEFROMTHELETTERABELOWMIDDLEC
```

### Method C: Rendering and Visual Inspection (Verification)
* This method will not help find the flag.
* This method is only useful to experiment with Lilypond's formatting of pitches.

1. Compile the `.ly` file using **Frescobaldi** or the LilyPond CLI:
   ```bash
   lilypond HomeCweetHome2.ly
   ```
2. Open the generated PDF (HomeCweetHome2.pdf).
3. Count the note positions visually.
4. Cross-reference the PDF against the `.ly` file for confirmation.

---

## The Final Flag

**Flag:** `DISTANCE_FROM_THE_LETTER_A_BELOW_MIDDLE_C` (or variants: `DISTANCEFROMTHELETTERABELOWMIDDLEC`, `distance_from_the_letter_a_below_middle_c`)

**Explanation of the Message:**
- "Middle C" is a music theory concept—the note C located in the middle of the piano keyboard (C4 in scientific pitch notation).
- The encoding scheme uses octaves and pitch positions *relative to Middle C*, but specifically the closest relative pitch *A* below *Middle C* — hence the meta-reference to the very concept that underlies the cipher.


---

## Common Mistakes & Pitfalls

### Mistake 1: Confusing NoteDuration/PitchDuration/PitchOrderingIndexComment with NoteName/PitchName
**Error:** "Note `c'4` is worth 4 quarter-notes, so it represents the number 4."
**Why it fails:** The duration (`4`) is metadata for audio playback, not part of the encoding. Only the comment/index number (#N, e.g. `% #26`) and pitch name that follows (e.g., `ctqs''`) encode information.
**Correct approach:**  
- Ignore the `4`, `8`, `2`, `16`, etc. in something like `a'''4` or `ctqs16`.
- Use the COMMENT index (#N), then find what NOTE is there (under it), then look that NOTE up in the 0-25 table to get an English letter. 

### Mistake 2: Trying to Decode the Entire Sequence  
**Error:** Attempting to decode ALL notes (at comment indices from #0 to end) as a message.  
**Why it fails:**  
- Indices 0–25 are the *definition* of the cipher, not data. They establish the lookup table.  
- After the participant 1) correctly decodes the first 4 or so pitches and 2) realizes they form the pitch-name pattern "A B C D ..." and then 3) the participant realizes they need to convert them to English letters "A B C D E F G H I J ...", the remaining indices of the alphabet are unnecessary.  
**Correct approach:**  
- Skip the first 26 (0-25) pitches, as they define the cipher, not the message.  
- Only decode the pitches at comment indices 26 and onward.  

### Mistake 3: Interpreting Note Frequency or Duration as Data
**Error:** "The note `c'4` has a frequency of ~262 Hz, so it encodes the number 262."
**Why it fails:** Frequency encoding would require specialized tools; the challenge explicitly uses indices.
**Correct approach:** The indices in the comments are the *only* data source.

### Mistake 4: Over-Interpreting the Curly Brace Clue
**Error:** "I need to find `{` and `}` in the file to extract the flag."
**Why it fails:** The subtitle says the flag is NOT enclosed in `{}`. The `flag` keyword is a logical marker, not a literal string.
**Correct approach:** The word "flag" is implicit in the structure; the extracted word is the flag.

### Mistake 5: Case Sensitivity and Spacing
**Error:** Submitting `DISTANCE_FROM_THE_LETTER_A_BELOW_MIDDLE_C` vs. `DISTANCEFROMTHELETTERABELOWMIDDLEC` vs. `distance_from_the_letter_a_below_middle_c` and getting the wrong one.
**Why it happens:** Different CTF platforms have different flag formats.
**Mitigation:** Try common variants: uppercase, lowercase, with underscores, without underscores, with `FLAG` prefix, without prefix.

### Mistake 6: Misunderstanding LilyPond Syntax
**Error:** "The `\absolute` block must mean something special; it's part of the encoding."
**Why it fails:** `\absolute` is a LilyPond directive specifying pitch notation mode. It's metadata, not message data.
**Correct approach:** Ignore all LilyPond keywords. Extract only the indexed comments and note names.

---

## Participant Challenges

### Challenge 1: Unfamiliarity with LilyPond
**Explanation:** Many CTF participants have no prior exposure to music notation markup.
**Mitigation:**
- The challenge is solvable without understanding LilyPond at all.
- Participants can treat the `.ly` file as plain text and extract indices and note names via regex.
- Providing a `.pdf` alongside the `.ly` helps visual learners, though it's less actionable.

### Challenge 2: Assuming Music Theory is Central
**Impact:** Moderate to High.
**Explanation:** Participants might waste time analyzing intervals, harmonies, or rhythm, assuming the music *itself* encodes data.
**Mitigation:**
- The hint subtitle ("flag keyword...extracted word") strongly suggests a symbolic, not sonic, solution.

### Challenge 3: Regex Extraction Complexity
**Explanation:** Extracting indices via regex can be tricky if line breaks are inconsistent or if each pitch has an associated duration.
**Example failure:**
```python
pattern = r'# (\d+)\n(\w+)'  # Assumes consistent spacing, no duration, exact base/"middle" octave
# This will fail if any of the following varies: 1) indentation type (space, tab) and quantity, 2) quantity of blank lines between comment index and pitch, 3) presence of an appended note duration (e.g., `4`/`8`/`2`/`16`), 4) octave modifiers (e.g., `c'''`/`c,`/`c'`)
```
**Better pattern:**
```python
pattern = r'%\s*#(\d+)\s*(?:\n)*\s*([a-z]+[\',]*)'
# Uses:
# * \s    for flexible whitespace
# * ...*  for "0 or more contiguous occurrences"
# * ...+  for "1 or more contiguous occurrences"
# * [a-z] for forbidding duration integers (only accepts lowercase letters a through z)
# * [',]  for allowing octave markings apostrophe and comma
# * (...)   for remembering what specific data it found
# * (?:...) for forgetting what specific data it found
```

### Challenge 4: Index Off-by-One Errors
**Explanation:** If participants manually count indices or create their lookup table, they may map (indexOf_pitchName_a 0 → English letter B) instead of (indexOf_pitchName_a 0 → English letter A).
**Mitigation:** Double-check the first few mappings by cross-referencing the `.ly` file.

### Challenge 5: Enharmonic Naming Errors
**Explanation:** If participants manually count indices or create their lookup table, they may not realize that whole tones are not consistently mapped to sharped/flatted pitch names.
- E.g., participant may expect `E#`/`es` and `B#`/`bs` to exist, and therefore that `etqs` and `btqs` exist, despite those names *not* being unique note names and instead corresponding to `F`/`f` and `C`/`c`, and `fqs` and `cqs`, respectively.
- If the notes within a single octave were consistent, then notes `a, as, b, bs, c, cs, d, ds, e, es, f, fs, g, gs` would exist, which is 12+1+1 = 14 notes rather than the widely accepted 12 notes per octave.
  - In the case of 24-TET, this logically-consistent-yet-inaccurate ordering implies 24+2+2 = 28 notes per octave rather than the widely accepted 24 notes per octave. The 4 extra notes that aren't unique are `bs`/`btqs`/`es`/`etqs` (or equivalently `cf`/`ctqf`/`ff`/`ftqf`)
**Mitigation:** Double-check the first 7 or so mappings by cross-referencing the `.ly` file.


### Issue: "I can't find the notes section"
**Solution:** Use `Ctrl+F` to search for comment `#0` or `#1`. The noteNames section starts shortly after.

### Issue: "I'm getting the wrong letters"
**Solution:** 
1. Double-check that you're reading the comment index correctly (e.g., `% #26` means commentIndex 26).
2. Verify the note name on the *next non-empty line* after the comment.
3. Cross-reference the note against the lookup table twice.

### Issue: "My letters don't spell English words, just English letters"
**Solution:** 
- Ensure you're starting from comment index #26 (not #0).
- Verify you're reading each note name correctly (distinguish between `c'`, `cs'`, `c''`, etc.).
- Check for typos in the lookup table.


---

## Verification Checklist

Before submitting your flag, verify:

- [ ] I extracted Lilycode comment indices 26 through to the end
- [ ] Each comment index maps to exactly one note in the file (the following line in the Lilycode is the pitch/note)
- [ ] I cross-referenced each note against the 26-note lookup table
- [ ] I converted each pitch index to an English letter (0→A, 1→B, ..., 25→Z)
- [ ] I concatenated all decoded English letters in order
- [ ] My result contains recognizable English words, not just English letters
- [ ] I extracted the portion after "FLAG" as the flag text


---

## Alternative Approaches (If Initial Method Fails)

### If Regex Extraction Fails
- Manually extract indices and notes using a text editor's find function (e.g., CTRL+H).
- Copy-paste the relevant section into a spreadsheet and sort by each Lilycode comment's index.
- Use a Python loop with file I/O to read line-by-line and match patterns iteratively.

---

## Summary Table

| Aspect | Details |
|--------|---------|
| **Data Source** | LilyPond `.ly` file with numerically indexed/ordered comments |
| **Cipher Type** | A0_Z25 Substitution (PitchName → PitchIndex → EnglishLetter) |
| **Lookup Table** | PitchIndices 0–25 map to A–Z via 24TET chromatic multi-octave pitch sequence |
| **Encoded Data** | CommentIndices 26 to end |
| **Decoding Steps** | Extract PitchName at each CommentIndex number → Match pitchName to English letters → Concatenate English letters |
| **Output Format** | `DISTANCEFROMTHELETTERABELOWMIDDLEC` or similar variant |
| **Music Knowledge** | 24-TET Chromatic scale, octave notation, enharmonic note names, Lilypond's `\language "english"` naming convention |
| **Tools Needed** | Text editor, RegEx with Python/BASH (or manual extraction)|
| **Time to Solve** | 15–45 minutes (manual), 5–20 minutes (automated) |

---

## References & Learning Resources  

1. **LilyPond Documentation:** https://lilypond.org/manuals.html  
2. **Musical terminology:** https://lilypond.org/doc/v2.26/Documentation/music-glossary/index.html  
3. **Chromatic Scale (Music):** https://en.wikipedia.org/wiki/Chromatic_scale  
4. **Middle C:** https://en.wikipedia.org/wiki/Middle_C  
5. **CTF Steganography Techniques:** https://owasp.org/www-community/attacks/Steganography  
6. **Python Regex Guide:** https://docs.python.org/3/library/re.html  

---

## Author's Intent  

**Mort** designed this challenge to:  
1. Introduce CTF participants to **non-traditional data formats** (music notation).  
2. Test the ability to **extract structured data** from a markup language without executing it.  
3. Mix typical cryptography concepts with more-niche data-dense Sheet Music concepts.  

---

**Solution Version:** 1.1  
**Last Updated:** 2025-Nov-04
 


<br>
<br>
<br>
<br>




# Manual Flag Extraction Walkthrough

## Step-by-Step Manual Decoding (Without Code)

This guide walks through extracting the flag manually using only a text editor and a lookup table.

---

## Phase 2: Extract the Message Indices (26–48)

Open `HomeCweetHome2.ly` in a text editor and find the notes section (around line 43+).

Look for comment lines starting with `% #` followed by a number. Extract only the indices **26 and onward**.

### Message Extraction (by hand)

Scan through the file from line 110 onwards and list out each index and its note:

```
...
% #26
bqs          ← Note: bqs
% #27
dqs'         ← Note: dqs'

% #28
a            ← Note: a
% #29
c'           ← Note: c'
... and so on
```

Create a table:

| Index | Note | Action |
|-------|------|--------|
| 26 | bqs  | Find bqs  in lookup table → It's at position 5 → **F** |
| 27 | dqs' | Find dqs' in lookup table → It's at position 11 → **L** |
| 28 | a    | Find a    in lookup table → It's at position 0 → **A** |
| 29 | c'   | Find c'   in lookup table → It's at position 6 → **G** |
| 30 | atqs | Find atqs in lookup table → It's at position 3 → **D** |
| 31 | cs'  | Find cs'  in lookup table → It's at position 8 → **I** |

---

## Phase 3: Map Each Note to Its Lookup Index

For each note in the message, find it in the lookup table:

### Example: Note f' at Index #26

1. **Lookup:** bqs appears at position **5** in the lookup table.
2. **Convert:** Position 5 = Letter **F**
3. **Record:** F

### Example: Note b' at Index #27

1. **Lookup:** dqs' appears at position **11** in the lookup table.
2. **Convert:** Position 11 = Letter **L**
3. **Record:** L

### Example: Note c' at Index #28

1. **Lookup:** a appears at position **0** in the lookup table.
2. **Convert:** Position 0 = Letter **A**
3. **Record:** A

---

## Phase 4: Decode the Complete Message

Continuing the process for all indices 26 through to the end:

| Index | Note | Lookup Position | Letter |
|-------|------|-----------------|--------|
|26|	bqs		|5	|F|
|27|	dqs'	|11	|L|
|28|	a		|0	|A|
|29|	c'		|6	|G|
|30|	atqs	|3	|D|
|31|	cs'		|8	|I|
|32|	fs'		|18	|S|
|33|	ftqs'	|19	|T|
|34|	a		|0	|A|
|35|	dtqs'	|13	|N|
|36|	as		|2	|C|
|37|	b		|4	|E|
|38|	bqs		|5	|F|
|39|	fqs'	|17	|R|
|40|	e'		|14	|O|
|41|	ds'		|12	|M|
|42|	ftqs'	|19	|T|
|43|	cqs'	|7	|H|
|44|	b		|4	|E|
|45|	dqs'	|11	|L|
|46|	b		|4	|E|
|47|	ftqs'	|19	|T|
|48|	ftqs'	|19	|T|
|49|	b		|4	|E|
|50|	fqs'	|17	|R|
|51|	a		|0	|A|
|52|	aqs		|1	|B|
|53|	b		|4	|E|
|54|	dqs'	|11	|L|
|55|	e'		|14	|O|
|56|	gs'		|22	|W|
|57|	ds'		|12	|M|
|58|	cs'		|8	|I|
|59|	atqs	|3	|D|
|60|	atqs	|3	|D|
|61|	dqs'	|11	|L|
|62|	b		|4	|E|
|63|	as		|2	|C|

### Concatenate All Letters

Reading from top to bottom:
```
F L A G D I S T A N C E F R O M T H E L E T T E R A B E L O W M I D D L E C
```

**Full Encoded Message:** `FLAGDISTANCEFROMTHELETTERABELOWMIDDLEC`

---

## Phase 5: Extract the Flag

The subtitle in the file says:
> "'flag' keyword is included here, but not '{' nor '}'.  The extracted word is the flag."

This means:
- The word "flag" is the intro marker
- Everything after "flag" is the flag itself
- No curly braces are involved

**Extracting the flag:**
- Input: `FLAGDISTANCEFROMTHELETTERABELOWMIDDLEC`
- Keyword: `FLAG`
- Extracted Flag: `DISTANCEFROMTHELETTERABELOWMIDDLEC`

Or, in common CTF formats:
- `flag{DISTANCEFROMTHELETTERABELOWMIDDLEC}`
- `FLAG{DISTANCEFROMTHELETTERABELOWMIDDLEC}`







# HOME CWEET HOME 2 - CTF CHALLENGE QUICK REFERENCE

CHALLENGE TYPE:    Sheet Music  
DIFFICULTY:        Medium  
TIME TO SOLVE:     10-45 minutes (coded vs. manual)  

### THE SOLUTION IN 60 SECONDS

1. QUIRK: The .ly file has indexed comments (% #0, % #1, % #2, ...)  

2. INSIGHT:  
   - Indices 0-25 define cipher (note pitch → letter A-Z)  
   - Indices 26 through to end encode the message (note pitch → letter via cipher)  

3. RECOVERY:  
   - Extract note at index 26: "bqs"  → maps to position 5 → Letter "F"  
   - Extract note at index 27: "dqs'" → maps to position 11 → Letter "L"  
   - Continue for indices 26-end...  
   - Concatenate all letters: FLAGDISTANCEFROMMIDDLEC  
   - Extract flag: DISTANCEFROMMIDDLEC  



### MESSAGE DECODING (Indices 26-end)

| Index | Note | Lookup Position | Letter |
|-------|------|-----------------|--------|
|26|	bqs		|5	|F|
|27|	dqs'	|11	|L|
|28|	a		|0	|A|
|29|	c'		|6	|G|
|30|	atqs	|3	|D|
|31|	cs'		|8	|I|
|32|	fs'		|18	|S|
|33|	ftqs'	|19	|T|
|34|	a		|0	|A|
|35|	dtqs'	|13	|N|
|36|	as		|2	|C|
|37|	b		|4	|E|
|38|	bqs		|5	|F|
|39|	fqs'	|17	|R|
|40|	e'		|14	|O|
|41|	ds'		|12	|M|
|42|	ftqs'	|19	|T|
|43|	cqs'	|7	|H|
|44|	b		|4	|E|
|45|	dqs'	|11	|L|
|46|	b		|4	|E|
|47|	ftqs'	|19	|T|
|48|	ftqs'	|19	|T|
|49|	b		|4	|E|
|50|	fqs'	|17	|R|
|51|	a		|0	|A|
|52|	aqs		|1	|B|
|53|	b		|4	|E|
|54|	dqs'	|11	|L|
|55|	e'		|14	|O|
|56|	gs'		|22	|W|
|57|	ds'		|12	|M|
|58|	cs'		|8	|I|
|59|	atqs	|3	|D|
|60|	atqs	|3	|D|
|61|	dqs'	|11	|L|
|62|	b		|4	|E|
|63|	as		|2	|C|

### Concatenated Letters:
`F L A G D I S T A N C E F R O M T H E L E T T E R A B E L O W M I D D L E C`  


### FINAL FLAG  

EXTRACTED MESSAGE:  
- `FLAGDISTANCEFROMTHELETTERABELOWMIDDLEC`  

EXTRACTED FLAG:  
- `DISTANCEFROMTHELETTERABELOWMIDDLEC`  
  
COMMON FORMATS:  
✓ flag{DISTANCEFROMTHELETTERABELOWMIDDLEC}  
✓ FLAG{DISTANCEFROMTHELETTERABELOWMIDDLEC}  
✓ DISTANCEFROMTHELETTERABELOWMIDDLEC			(not this)  
✓ distancefromtheletterabelowmiddlec			(not this)  
✓ distance_from_the_letter_a_below_middle_c	(not this)  


### MUSIC THEORY  
  
24-TONE CHROMATIC SCALE (single octave):  
- a,aqs,as,atqs, b,bqs, c,cqs,cs,ctqs, d,dqs,ds,dtqs, e,eqs, f,fqs,fs,ftqs, g,gqs,gs,gtqs  
  - (uses only variations of sharps, no variations of flats. Uses Lilypond `\language "english"`)  
  
ENHARMONIC NOTES ("a note is as pretty by any other name"):  
- The multiple ways of writing enharmonic notes (e.g., `B`/`b`/`Cb`/`cf`, `C`/`c`/`B#`/`bs`, `C𝄰`/`ctqs`/`dqf`, `E𝄱`/`eqs`/`fqf`/`F𝄬`)  
- Which notes are typically included in 24TET (sharps vs flats vs both)  
- Various ways to write sharps and flats like `s`/`#` and `f`/`b`, quarter- and threeQuarter- variations of each of {sharps, flats}  

OCTAVE NOTATION:  
- `c'` (1 octave up),   `c''` (2 octaves up),   `c'''` (3 octaves up)  
- `c,` (1 octave down), `c,,` (2 octaves down), `c,,,` (3 octaves down)    
  
MIDDLE C:  
- Reference pitch at center of piano keyboard  
  
SHARP (♯):  
- In LilyPond, written as "s" → `c` becomes `cs`/`C♯`  
  
FRACTIONS OF SHARP:  
- In LilyPond, 0.5-of-a-Sharp (i.e., `quarter-sharp`/`1/4 #`, quarter-of-whole-tone) is written as `qs` → `c` becomes `cqs`  
- In LilyPond, 1.5-of-a-Sharp (i.e., `three-quarter-sharp`/`3/4 #`, three-quarter-of-whole-tone) is written as `tqs` → `c` becomes `ctqs`
- In Lilypond, flats operate on a similar principle (`qf`, `tqf`).

NO MUSIC PLAYBACK NEEDED - This is pure symbol decoding!

### FLAG EXTRACTION METHODS

METHOD 1 (FASTEST): Python Script  
`$ python3 solveHomeCweetHome2.py`	# Linux  
`$ py solveHomeCweetHome2.py`		# Windows  
Output: `DISTANCEFROMTHELETTERABELOWMIDDLEC`

METHOD 2 (MANUAL): Text Editor + Lookup Table
1. Open HomeCweetHome2.ly in text editor
2. Find lines with "% #26" through to the end
3. Note the note name on the line following each comment
4. Cross-reference with lookup table
5. Concatenate all letters


### KEY INSIGHT RECAP
* The challenge IS about pattern recognition and indexing
* The note pitches are just symbols for indices in a Lookup Table.
* CommentIndices 0-25 define the cipher; CommentIndices 26-end encode the message
* The message contains the word "FLAG" followed by the actual flag
