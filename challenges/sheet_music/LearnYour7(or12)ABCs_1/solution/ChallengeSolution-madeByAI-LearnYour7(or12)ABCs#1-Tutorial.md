# CTF Challenge Solution: Learn Your 7 (or 12) ABCs 1  

## Challenge Overview
**Challenge Name:** Learn Your 7 (or 12) ABCs 1  
**Creator:** Mort  
**Difficulty:** training  
**Category:** Steganography / Sheet Music  

**ChallengeDescription_Themed_ViewableByParticipant:**  
Heard by ear and transcribed to sheet music, a security officer had a hunch that note names present in the sheet music covertly sound the song of the crew's flag. Can you verify their hunch?  

**Flags that participant can submit:**
- flag{cabbage}
- flag{CABBAGE}
- FLAG{cabbage}
- FLAG{CABBAGE}

**Invalid Flags:**
- CABBAGE  
- cabbage  

**Files Provided To Participant:**  
- dist/LearnYour7(or12)ABCs_1-Tutorial.mid
- dist/LearnYour7(or12)ABCs_1-Tutorial.pdf

---

## Step 1: Noticeable Quirks About the Data

### A) Unusual File Format
- The challenge is delivered as a PDF and audio file (`.mid`). Participants do not receive the source Lilycode that generated these two files.

### B) Short song
- There aren't many data locations to get confused about possibly storing the flag. There's a limited number of places where the data could reasonably exist.  
- There are only three measures, each with a unique text label.

### C) Deliberate Message in the Subtitle
```lilypond
subtitle = "'flag{', `}` keywords not included here.  The extracted word is the flag."
```
This subtitle is **not** describing the visual appearance. Instead, it's telling you:
- A word called "flag" does not exist in the data
- It's not surrounded by curly braces `{}`



## Solution
* 0) Noticeable quirk about the data: Listening to the recording makes it seem like each measure is just a variation of the same overall theme.
* 1) Technique: Get name of each note within the first measure. Requires participant being aware that typical note names are A,B,C,D,E,F,G, and where (vertically) those note names exist on the Treble clef staff.
     **Match each note's pitch to its corresponding English letter** using the lookup table (A->A, B->B, C->C, D->D, E->E, F->F, G->G).
     **Concatenate the English letters** to form the flag.
* 2) Flag Recovery: The first 7 note names as a string is the flag.


## Notes/Music Knowledge Required (To Understand the Challenge)
* 0) The musical pitches on a staff that visually correspond to pitches A,B,C,D,E,F,G
* 1) The 1st and 2nd measures provide the flag directly and easily, but the following measures can also give you the flag if you're an expert in interpreting transpositions (I am not, but Lilypond software allows easy transposition).
* 2) There are very few complexities here, with no chords/voices, no changing tempos, equivalent durations (quarter) for all notes, but there is use of a fermata, vertical repeat bars starting and ending in the 2nd measure, and a single sharp in the transposed measure.

### Nice-to-Have (Not Required)

- LilyPond syntax (`\version`, `\header`, `\score`, etc.) is **irrelevant** to the solution. Participants can ignore all markup and focus solely on the note names.
- Music theory concepts like intervals, clefs, or time signatures are **not tested** here. The challenge is purely steganographic.

---

## Common Mistakes & Pitfalls

### Mistake 1: Confusing NoteDuration/PitchDuration/PitchOrderingIndexComment with NoteName/PitchName
**Error:** "Note `c'4` is worth 4 quarter-notes, so it represents the number 4."
**Why it fails:** The duration (`4`) is metadata for audio playback, not part of the encoding. Only the pitch name encodes information.
**Correct approach:**  
- Ignore the `4`, `8`, `2`, `16`, etc. in something like `a'''4` or `ctqs16`.

### Mistake 2: Trying to Decode the Entire Sequence  
**Error:** Attempting to decode ALL notes as a message.  
- Each measure contains the whole flag. Concatenating the three measures just needlessly triples the flag.

### Mistake 3: Interpreting Note Frequency or Duration as Data
**Error:** "The note `c'4` has a frequency of ~262 Hz, so it encodes the number 262."
**Why it fails:** Frequency encoding would require specialized tools; the challenge explicitly uses note names.

### Mistake 4: Over-Interpreting the Curly Brace Clue
**Error:** "I need to find `{` and `}` in the file to extract the flag."
**Why it fails:** The subtitle says the flag is NOT enclosed in `{}`. The `flag` keyword is a logical marker, not a literal string.
**Correct approach:** The word "flag" is implicit in the structure; the extracted word is the flag.

### Mistake 5: Case Sensitivity and Spacing
**Error:** Submitting `CABBAGE` vs. `cabbage` and getting the wrong one.
**Why it happens:** Different CTF platforms have different flag formats.
**Mitigation:** Try common variants: uppercase, lowercase, with underscores, without underscores, with `FLAG` prefix, without prefix.

---

## Participant Challenges

### Challenge 1: Unfamiliarity with Sheet Music
**Explanation:** Many CTF participants have no prior exposure to music notation markup.
**Mitigation:**
- Providing a list of vetted resources/websites to learn more.

### Challenge 2: Assuming Music Theory is Central
**Impact:** Moderate to High.
**Explanation:** Participants might waste time analyzing intervals, harmonies, or rhythm, assuming the music *itself* encodes data.
**Mitigation:**
- The hint subtitle ("flag keyword...extracted word") strongly suggests a symbolic, not sonic, solution.


---

## Verification Checklist

Before submitting your flag, verify:

- [ ] I converted each pitch to an English letter  (A->A, B->B, C->C, D->D, E->E, F->F, G->G)
- [ ] I concatenated all decoded English letters in order
- [ ] My result contains recognizable English words, not just English letters
- [ ] I added "FLAG{", "}" before and after, respectively, the extracted plaintext portion, as the flag text to submit

---

## Summary Table

| Aspect | Details |
|--------|---------|
| **Data Source** | PDF |
| **Cipher Type** | [A..G] -> [A..G] (PitchName → EnglishLetter) |
| **Lookup Table** | Substitution Cipher:  [A..G] -> [A..G] (PitchName → EnglishLetter) via 7TET/12TET chromatic single-octave pitch sequence |
| **Decoding Steps** | Extract PitchName  → Match pitchName to English letters → Concatenate English letters |
| **Output Format** | `CABBAGE` or similar variant |
| **Music Knowledge** | 7-TET or 12-TET Chromatic scale |
| **Tools Needed** | PDF viewer |
| **Time to Solve** | 0.5–15 minutes |

---

## References & Learning Resources

1. **LilyPond Documentation:**
- https://lilypond.org/manuals.html
- https://lilypond.org/doc/v2.26/Documentation/music-glossary/index.html
3. **Chromatic Scale (Music):** https://en.wikipedia.org/wiki/Chromatic_scale

---

## Author's Intent

**StevieoXOR** designed this challenge to:
1. Introduce CTF participants to **non-traditional data formats** (music notation).
2. Test the ability to **extract structured data** from a markup language without executing it.
3. Mix typical cryptography concepts with more-niche data-dense Sheet Music concepts.

---

**Solution Version:** 1.0  
**Last Updated:** 2025-09-14
