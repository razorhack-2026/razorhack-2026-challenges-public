# CTF Challenge Solution: Home Cweet Home 1

## Challenge Overview
**Challenge Name:** Home Cweet Home 1  
**Creator:** Mort  
**Difficulty:** medium  
**Category:** Steganography / Sheet Music  

**ChallengeDescription_Themed_ViewableByParticipant**  
Heard by microphone recording and transcribed to sheet music by a staff member with perfect pitch, a security officer noticed that many notes gradually increased in pitch while seeming out of tune, possibly an issue with the microphone or the security team's transcriber, and that the notes after the ascent sounded like they were trying to form a song, but failing. Can you determine whether this series of recorded sounds is benign and simply unpleasant, or covertly transmitting data?

**Flags:**  
- flag{distancefrommiddlec}
- flag{DISTANCEFROMMIDDLEC}
- FLAG{distancefrommiddlec}
- FLAG{DISTANCEFROMMIDDLEC}

**Files:**  
- dist/HomeCweetHome1.ly
- dist/HomeCweetHome1.pdf
- dist/HomeCweetHome1.mid

---

## Step 1: Noticeable Quirks About the Data

### A) Unusual File Format
- The challenge is delivered as a **LilyPond file** (.ly), a specialized markup language for music notation—uncommon in CTF challenges, which typically use images, text, or code.
- Most participants won't immediately recognize LilyPond syntax and may assume this is purely a music challenge.

### B) Indexed Comments Instead of Note Names
```lilypond
% #0
c'4           
% #1
cs'           
% #2
d'
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
While pitches at comments #0–#25 show a clear chromatic pattern across octaves, the remaining pitches (indicated by comment `% #26` and onward) get reused (e.g., `f'` appears at both #5 and #26).  
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

These first 26 notes establish the A0_Z25 cipher:

| Index | Note | Letter || Index | Note | Letter |
|-------|------|--------|-|-------|------|--------|
| 0 | c' | A  || 13 | cs'' | N |
| 1 | cs' | B || 14 | d'' | O |
| 2 | d' | C  || 15 | ds'' | P |
| 3 | ds' | D || 16 | e'' | Q |
| 4 | e' | E  || 17 | f'' | R |
| 5 | f' | F  || 18 | fs'' | S |
| 6 | fs' | G || 19 | g'' | T |
| 7 | g' | H  || 20 | gs'' | U |
| 8 | gs' | I || 21 | a'' | V |
| 9 | a' | J  || 22 | as'' | W |
| 10 | as' | K || 23 | b'' | X |
| 11 | b' | L  || 24 | c''' | Y |
| 12 | c'' | M || 25 | cs''' | Z |

**Memorize this table or save it for reference.**


## Music Knowledge Required

### Why This Table's Mapping (PitchName->EnglishLetter) Works
- **Chromatic completeness:** The 12-tone chromatic scale (C, C♯, D, D♯, E, F, F♯, G, G♯, A, A♯, B) repeats across three octaves (', '', '''), yielding 12*3=36 unique pitches — more than enough for 26 letters.
- **Systematic ordering:** Notes 0–11 span one chromatic octave, 12–23 span the next, and 24–25 start a third. This creates an intuitive, unambiguous mapping.
- **Non-musical participant advantage:** You don't need to *hear* the music or understand intervals; you only need to read the pitch at each index number, determine which octave the pitch is in (number of apostrophes/commas), know about the multiple ways of writing enharmonic notes (e.g., `B`/`b`/`Cb`/`cf`, `C`/`c`/`B#`/`bs`), and which notes are typically included in 12TET (sharps vs flats vs both).

### Essential (To Understand the Challenge)
1. **Chromatic Scale:** The 12 semi-tones in Western music (C, C♯, D, D♯, E, F, F♯, G, G♯, A, A♯, B).
   - Participants unfamiliar with sharps (♯) should recognize that `cs` = C sharp.
   
2. **Octave Notation:** 
   - `c'` = C, but in the octave above Middle C  
	 Equivalently 6 whole tones above Middle C
     Equivalently 12 semi-tones (i.e., sequential pitches) above Middle C  
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
   f'            
   % #27
   b'            
   % #28
   c'            
   ```
4. Map to letters using the lookup table:
   - #26 → f' → F
   - #27 → b' → L
   - #28 → c' → A
   - ... and so on
5. **Result:** `FLAGDISTANCEFROMIDDLEC`

### Method B: Programmatic Extraction (Scalable)

Here's a Python solution (located in `solution/solveHomeCweetHome1.py`) that parses the LilyPond file automatically (partially created via AI, fixed (a lot) by challenge creator):

```python
import re

def decode_lilypond_flag(filepath):
	"""Extract and decode the embedded flag from a LilyPond file."""

	"""
	| Index | Note | Letter | | Index | Note | Letter |
	|-------|------|--------|-|-------|------|--------|
	| 0     | c'   | A      | | 13    | cs'' | N |
	| 1     | cs'  | B      | | 14    | d''  | O |
	| 2     | d'   | C      | | 15    | ds'' | P |
	| 3     | ds'  | D      | | 16    | e''  | Q |
	| 4     | e'   | E      | | 17    | f''  | R |
	| 5     | f'   | F      | | 18    | fs'' | S |
	| 6     | fs'  | G      | | 19    | g''  | T |
	| 7     | g'   | H      | | 20    | gs'' | U |
	| 8     | gs'  | I      | | 21    | a''  | V |
	| 9     | a'   | J      | | 22    | as'' | W |
	| 10    | as'  | K      | | 23    | b''  | X |
	| 11    | b'   | L      | | 24    | c''' | Y |
	| 12    | c''  | M      | | 25    | cs'''| Z |
	"""
	# Goal: Mapping: pitch_index (int) OR note_name (str) -> English_letter (A-Z)
	# index_to_letter = {
	# 	0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F',
	# 	6: 'G', 7: 'H', 8: 'I', 9: 'J', 10: 'K', 11: 'L',
	# 	12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R',
	# 	18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X',
	# 	24: 'Y', 25: 'Z'
	# }
  
	# Intermediate Mapping 1: Index -> Note Name (apostrophes preserved)
	index_to_note = {
		0: "c'", 1: "cs'", 2: "d'", 3: "ds'", 4: "e'", 5: "f'",
		6: "fs'", 7: "g'", 8: "gs'", 9: "a'", 10: "as'", 11: "b'",
		12: "c''", 13: "cs''", 14: "d''", 15: "ds''", 16: "e''", 17: "f''",
		18: "fs''", 19: "g''", 20: "gs''", 21: "a''", 22: "as''", 23: "b''",
		24: "c'''", 25: "cs'''"
	}
	# Intermediate Mapping 2: Note Name -> English Letter
	note_to_letter = {
		"c'": 'A', "cs'": 'B', "d'": 'C', "ds'": 'D', "e'": 'E', "f'": 'F',
		"fs'": 'G', "g'": 'H', "gs'": 'I', "a'": 'J', "as'": 'K', "b'": 'L',
		"c''": 'M', "cs''": 'N', "d''": 'O', "ds''": 'P', "e''": 'Q', "f''": 'R',
		"fs''": 'S', "g''": 'T', "gs''": 'U', "a''": 'V', "as''": 'W', "b''": 'X',
		"c'''": 'Y', "cs'''": 'Z'
	}

	def get_note_from_index(index: int) -> str:
		"""Returns pitch string with apostrophes intact."""
		return index_to_note.get(index, "[BAD_NOTE]")

	def get_letter_from_note(note: str) -> str:
		"""Returns English letter corresponding to pitch string."""
		return note_to_letter.get(note, "[BAD_LETTER]")

	def index_to_letter_chained(index: int) -> str:
		"""Chained execution: Index -> Note -> Letter."""
		note = get_note_from_index(index)
		return get_letter_from_note(note)
	
	with open(filepath, 'r') as f:
		content = f.read()
	
	# Find all lines with comment indices: % #NUMBER  (e.g., "% #0")
	# followed by a note on the next non-empty line
	pattern = r'%\s*#(\d+)\s*\n\s*(\w+[\'\"]*)'
	matches = re.findall(pattern, content)
	
	# Extract indices >= 26 (the encoded message)
	extracted_message, msg_after_definition = [], []
	for index_str, note in matches:
		# print(get_letter_from_note(note))
		msg_after_definition.append(get_letter_from_note(note))
		index = int(index_str)
		if index >= 26:  # Skip the lookup table definition pitches (0-25)
			extracted_message.append(get_letter_from_note(note))
	
	return ''.join(msg_after_definition), ''.join(extracted_message)

# Usage
LilycodeFilepath = '../dist/HomeCweetHome1.ly'	# MAY NEED TO CHANGE THIS FILEPATH
flag_strs = decode_lilypond_flag(LilycodeFilepath)
print(f"Encoded Message(s):")
[print(f"* {flag}") for flag in flag_strs]
# Expected: FLAGDISTANCEFROMMIDDLEC
```

**Output:**
```
Encoded Message(s):
* ABCDEFGHIJKLMNOPQRSTUVWXYZFLAGDISTANCEFROMMIDDLEC
* FLAGDISTANCEFROMMIDDLEC
```

### Method C: Rendering and Visual Inspection (Verification)
* This method will not help find the flag.
* This method is only useful to experiment with Lilypond's formatting of pitches.

1. Compile the `.ly` file using **Frescobaldi** or the LilyPond CLI:
   ```bash
   lilypond HomeCweetHome1.ly
   ```
2. Open the generated PDF (HomeCweetHome1.pdf).
3. Count the note positions visually.
4. Cross-reference the PDF against the `.ly` file for confirmation.

---

## The Final Flag

**Flag:** `DISTANCE_FROM_MIDDLE_C` (or variants: `DISTANCEFROMMIDDLEC`, `distance_from_middle_c`)

**Explanation of the Message:**
- "Middle C" is a music theory concept—the note C located in the middle of the piano keyboard (C4 in scientific pitch notation).
- The encoding scheme uses octaves and pitch positions *relative to Middle C*—hence the meta-reference to the very concept that underlies the cipher.

---

## Common Mistakes & Pitfalls

### Mistake 1: Confusing NoteDuration/PitchDuration/PitchOrderingIndexComment with NoteName/PitchName
**Error:** "Note `c'4` is worth 4 quarter-notes, so it represents the number 4."
**Why it fails:** The duration (`4`) is metadata for audio playback, not part of the encoding. Only the comment/index number (#N, e.g. `% #26`) and pitch name that follows (e.g., `cs''`) encode information.
**Correct approach:**  
- Ignore the `4`, `8`, `2`, `16`, etc. in something like `a'''4` or `cs16`.
- Use the COMMENT index (#N), then find what NOTE is there (under it), then look that NOTE up in the 0-25 table to get an English letter. 

### Mistake 2: Trying to Decode the Entire Sequence  
**Error:** Attempting to decode ALL notes (at comment indices from #0 to end) as a message.  
**Why it fails:**  
- Indices 0–25 are the *definition* of the cipher, not data. They establish the lookup table.  
- After the participant 1) correctly decodes the first 4 or so pitches and realizes they form the pitch-name pattern "C D E F ..." and then 2) the participant realizes they need to convert and transpose them down to English letters "A B C D E F G H I J ...", the remaining indices of the alphabet are unnecessary.  
**Correct approach:**  
- Skip the first 26 (0-25) pitches, as they define the cipher, not the message.  
- Only decode the pitches at comment indices 26 and onward.  

### Mistake 3: Interpreting Note {Frequency, Duration} as Data
**Error:** "The note `c'4` has a frequency of ~262 Hz, so it encodes the number 262."  
**Why it fails:** Frequency encoding would require specialized tools; the challenge explicitly uses pitches as indices that map to English letters.  
**Correct approach:** The pitches (and the ordering of them) in the comments are the *only* data source.  

### Mistake 4: Over-Interpreting the Curly Brace Clue (Looking for {curly braces} around the flag)
**Error:** "I need to find `{` and `}` in the file to extract the flag."  
**Why it fails:** The subtitle says the flag is NOT enclosed in `{}`. The `flag` keyword is a logical marker, not a literal string.  
**Correct approach:**  
- The word "flag" is implicit in the structure; the extracted word is the flag.
- The subtitle says braces are NOT included; "flag" is implicit

### Mistake 5: Case Sensitivity and Spacing ("I have the message but can't find the flag")  
**Error:** Submitting `FLAGDISTANCEFROMIDDLEC` vs. `distance_from_middle_c` and getting the wrong one.  
**Why it happens:** Different CTF platforms have different flag formats. The phrase "FLAGDISTANCEFROMMIDDLEC" literally contains the word FLAG followed by the flag text.  
**Mitigation:** Try common variants: uppercase, lowercase, with underscores, without underscores, with `FLAG` prefix, without prefix. Extract everything after "FLAG": `DISTANCEFROMMIDDLEC`  

### Mistake 6: Misunderstanding LilyPond Syntax  
**Error:** "The `\absolute` block must mean something special; it's part of the encoding."  
**Why it fails:** `\absolute` is a LilyPond directive specifying pitch notation mode. It's metadata, not message data.  
**Correct approach:** Ignore all LilyPond keywords. Extract only the indexed comments and note names.  

---

## Participant Challenges (Troubleshooting Manual/Programmatic Extraction)

### Challenge 1: Unfamiliarity with LilyPond
**Impact:** Moderate. Many CTF participants have no prior exposure to music notation markup.  
**Mitigation:**
- The challenge is solvable without understanding LilyPond at all.
- Participants can treat the `.ly` file as plain text and extract pitch orderings and note names via regex.
- Providing a `.pdf` alongside the `.ly` helps visual learners, though it's less actionable.

### Challenge 2: Assuming Music Theory is Central
**Impact:** Moderate to High. Participants might waste time analyzing intervals, harmonies, or rhythm, assuming the music *itself* encodes data.  
**Mitigation:**
- The hint subtitle ("flag keyword...extracted word") strongly suggests a *symbolic*, not sonic, solution. No need to listen to the ...`.mid` file.

### Challenge 3: Regex Extraction Complexity
**Impact:** Low. Extracting indices via regex can be tricky if line breaks are inconsistent or if each pitch has an associated duration (e.g., `4`/`8`/`2`/`16`).
**Example failure:**  
```python
pattern = r'# (\d+)\n(\w+)'  # Assumes consistent spacing
# This will fail if indentation or blank lines vary
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
- E.g., participant may expect `E#`/`es` and `B#`/`bs` to exist, despite those names *not* being unique note names and instead corresponding to `F`/`f` and `C`/`c` respectively.
- If the notes within a single octave were consistent, then notes `a, as, b, bs, c, cs, d, ds, e, es, f, fs, g, gs` would exist, which is 12+1+1 = 14 notes rather than the widely accepted 12 notes per octave.
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
| **Lookup Table** | PitchIndices 0–25 map to A–Z via 12TET chromatic multi-octave pitch sequence |
| **Encoded Data** | CommentIndices 26 to end |
| **Decoding Steps** | Extract PitchName at each CommentIndex number → Match pitchName to English letters → Concatenate English letters |
| **Output Format** | `DISTANCEFROMMIDDLEC` or similar variant |
| **Music Knowledge** | 12-TET Chromatic scale, octave notation, enharmonic note names, Lilypond's `\language "english"` naming convention |
| **Tools Needed** | Text editor, RegEx with Python/BASH (or manual extraction)|
| **Time to Solve** | 15–45 minutes (manual), 5–20 minutes (automated) |

---

## References & Learning Resources

1. **LilyPond Documentation:** https://lilypond.org/manuals.html
2. **Chromatic Scale (Music):** https://en.wikipedia.org/wiki/Chromatic_scale
3. **Middle C:** https://en.wikipedia.org/wiki/Middle_C
4. **CTF Steganography Techniques:** https://owasp.org/www-community/attacks/Steganography
5. **Python Regex Guide:** https://docs.python.org/3/library/re.html

---

## Author's Intent

**StevieoXOR** designed this challenge to:
1. Introduce CTF participants to **non-traditional data formats** (music notation).
2. Test the ability to **extract structured data** from a markup language without executing it.
3. Mix typical cryptography concepts with more-niche data-dense Sheet Music concepts.

The challenge *appears* to be about music theory but is actually about **pattern recognition and index mapping**.

---

**Solution Version:** 1.0  
**Last Updated:** 2025-09-01
 






# Manual Flag Extraction Walkthrough

## Step-by-Step Manual Decoding (Without Code)

This guide walks through extracting the flag manually using only a text editor and a lookup table.

---

## Phase 2: Extract the Message Indices (26–48)

Open `HomeCweetHome1.ly` in a text editor and find the notes section (around line 43+).

Look for comment lines starting with `% #` followed by a number. Extract only the indices **26 and onward**.

### Message Extraction (by hand)

Scan through the file from line 110 onwards and list out each index and its note:

```
Line 110-112:
% #26
f'            ← Note: f'

Line 115-117:
% #27
b'            ← Note: b'

Line 118-120:
% #28
c'            ← Note: c'

... and so on
```

Create a table:

| Index | Note | Action |
|-------|------|--------|
| 26 | f' | Find f' in lookup table → It's at position 5 → **F** |
| 27 | b' | Find b' in lookup table → It's at position 11 → **L** |
| 28 | c' | Find c' in lookup table → It's at position 0 → **A** |
| 29 | fs' | Find fs' in lookup table → It's at position 6 → **G** |
| 30 | ds' | Find ds' in lookup table → It's at position 3 → **D** |
| 31 | gs' | Find gs' in lookup table → It's at position 8 → **I** |

---

## Phase 3: Map Each Note to Its Lookup Index

For each note in the message, find it in the lookup table:

### Example: Note f' at Index #26

1. **Lookup:** f' appears at position **5** in the lookup table.
2. **Convert:** Position 5 = Letter **F**
3. **Record:** F

### Example: Note b' at Index #27

1. **Lookup:** b' appears at position **11** in the lookup table.
2. **Convert:** Position 11 = Letter **L**
3. **Record:** L

### Example: Note c' at Index #28

1. **Lookup:** c' appears at position **0** in the lookup table.
2. **Convert:** Position 0 = Letter **A**
3. **Record:** A

---

## Phase 4: Decode the Complete Message

Continuing the process for all indices 26 through to the end:

| Index | Note | Lookup Position | Letter |
|-------|------|-----------------|--------|
| 26 | f' | 5 | F |
| 27 | b' | 11 | L |
| 28 | c' | 0 | A |
| 29 | fs' | 6 | G |
| 30 | ds' | 3 | D |
| 31 | gs' | 8 | I |
| 32 | fs'' | 18 | S |
| 33 | g'' | 19 | T |
| 34 | c' | 0 | A |
| 35 | cs'' | 13 | N |
| 36 | d' | 2 | C |
| 37 | e' | 4 | E |
| 38 | f' | 5 | F |
| 39 | f'' | 17 | R |
| 40 | d'' | 14 | O |
| 41 | c'' | 12 | M |
| 42 | c'' | 12 | M |
| 43 | gs' | 8 | I |
| 44 | ds' | 3 | D |
| 45 | ds' | 3 | D |
| 46 | b' | 11 | L |
| 47 | e' | 4 | E |
| 48 | d' | 2 | C |

### Concatenate All Letters

Reading from top to bottom:
```
F L A G D I S T A N C E F R O M M I D D L E C
```

**Full Encoded Message:** `FLAGDISTANCEFROMMIDDLEC`

---

## Phase 5: Extract the Flag

The subtitle in the file says:
> "'flag' keyword is included here, but not '{' nor '}'.  The extracted word is the flag."

This means:
- The word "flag" is the intro marker
- Everything after "flag" is the flag itself
- No curly braces are involved

**Extracting the flag:**
- Input: `FLAGDISTANCEFROMMIDDLEC`
- Keyword: `FLAG`
- Extracted Flag: `DISTANCEFROMMIDDLEC`

Or, in common CTF formats:
- `flag{DISTANCEFROMMIDDLEC}`
- `FLAG{DISTANCEFROMMIDDLEC}`


---




# HOME CWEET HOME 1 - CTF CHALLENGE QUICK REFERENCE

CHALLENGE TYPE:    Sheet Music  
DIFFICULTY:        Medium  
TIME TO SOLVE:     5-30 minutes (coded vs. manual)  

### THE SOLUTION IN 60 SECONDS

1. QUIRK: The .ly file has indexed comments (% #0, % #1, % #2, ...)

2. INSIGHT: 
   - Indices 0-25 define cipher (note pitch → letter A-Z)
   - Indices 26 through to end encode the message (note pitch → letter via cipher)

3. RECOVERY:
   - Extract note at index 26: "f'" → maps to position 5 → Letter "F"
   - Extract note at index 27: "b'" → maps to position 11 → Letter "L"
   - Continue for indices 26-end...
   - Concatenate all letters: FLAGDISTANCEFROMMIDDLEC
   - Extract flag: DISTANCEFROMMIDDLEC



### MESSAGE DECODING (Indices 26-end)

INDEX | NOTE  | LOOKUP | LETTER | | INDEX | NOTE  | LOOKUP | LETTER
------|-------|--------|--------|-|-------|-------|--------|--------
26    | f'    | 5      | F      | | 37    | e'    | 4      | E
27    | b'    | 11     | L      | | 38    | f'    | 5      | F
28    | c'    | 0      | A      | | 39    | f''   | 17     | R
29    | fs'   | 6      | G      | | 40    | d''   | 14     | O
30    | ds'   | 3      | D      | | 41    | c''   | 12     | M
31    | gs'   | 8      | I      | | 42    | c''   | 12     | M
32    | fs''  | 18     | S      | | 43    | gs'   | 8      | I
33    | g''   | 19     | T      | | 44    | ds'   | 3      | D
34    | c'    | 0      | A      | | 45    | ds'   | 3      | D
35    | cs''  | 13     | N      | | 46    | b'    | 11     | L
36    | d'    | 2      | C      | | 47    | e'    | 4      | E
.     |       |       |         | | 48    | d'    | 2      | C

CONCATENATED: `F L A G D I S T A N C E F R O M M I D D L E C`


### FINAL FLAG
EXTRACTED MESSAGE:  
- `FLAGDISTANCEFROMMIDDLEC`

EXTRACTED FLAG:  
- `DISTANCEFROMMIDDLEC`  

COMMON FORMATS:  
✓ flag{DISTANCEFROMMIDDLEC}  
✓ FLAG{DISTANCEFROMMIDDLEC}  
✓ DISTANCEFROMMIDDLEC		(not this)  
✓ distancefrommiddlec		(not this)  
✓ distance_from_middle_c	(not this)  


### MUSIC THEORY  
12-TONE/12-TET CHROMATIC SCALE (single octave):  
- C, C♯, D, D♯, E, F, F♯, G, G♯, A, A♯, B
- c, cs, d, ds, e, f, fs, g, gs, a, as, b
  - (both these examples use only variations of sharps, no variations of flats. 2nd example uses Lilypond `\language "english"`)

ENHARMONIC NOTES ("a note is as pretty by any other name"):  
- The multiple ways of writing enharmonic notes (e.g., `B`/`b`/`Cb`/`cf`, `C`/`c`/`B#`/`bs`)  
- Which notes are typically included in 12TET (sharps vs flats vs both)  
- Various ways to write sharps and flats like `s`/`#` and `f`/`b`

OCTAVE NOTATION:
- `c'` (1 octave), `c''` (2 octaves), `c'''` (3 octaves)

MIDDLE C:  
- The reference pitch at center of piano keyboard  

SHARP (♯):  
- In LilyPond, written as "s" → `c` becomes `cs`/`C♯`

NO MUSIC PLAYBACK NEEDED - This is pure symbol decoding!  




### FLAG EXTRACTION METHODS

METHOD 1 (FASTEST): Python Script  
`$ python3 solveHomeCweetHome1.py`	# Linux  
`$ py solveHomeCweetHome1.py`		# Windows  
Output: `FLAGDISTANCEFROMMIDDLEC`  

METHOD 2 (MANUAL): Text Editor + Lookup Table  
1. Open HomeCweetHome1.ly in text editor  
2. Find lines with "% #26" through to the end  
3. Note the note name on the line following each comment  
4. Cross-reference with lookup table  
5. Concatenate all letters  



### KEY INSIGHT RECAP
* The challenge IS about pattern recognition and indexing  
* The note pitches are just symbols for indices in a Lookup Table.  
* CommentIndices 0-25 define the cipher; CommentIndices 26-end encode the message  
* The message contains the word "FLAG" followed by the actual flag  
