# CTF Challenge Solution: 1 2 3 FOUR  

## Challenge Overview  
**Challenge Name:** 1 2 3 FOUR  
**Author:** Mort  
**Difficulty:** medium  
**Category:** Steganography / Sheet Music  

**ChallengeDescription_Themed_ViewableByParticipant:**  
Heard by microphone recording and transcribed to sheet music, a security officer noticed a familiar pattern in the beginning sounds. Can you determine whether this series of recorded sounds is benign and simply Avant-Garde, or covertly transmitting data?  

**Flags:**  
- flag{usefourthnotepermeasure}  
- flag{USEFOURTHNOTEPERMEASURE}  
- FLAG{usefourthnotepermeasure}  
- FLAG{USEFOURTHNOTEPERMEASURE}  

**Files Provided To Participant:**  
- dist/123FOUR_4ppc_7divRand_12divData.pdf  
- dist/123FOUR_4ppc_7divRand_12divData.mid  




## STEP BY STEP SOLUTION
Starting at measure 27 because I noticed that the 4th note of each of the first 26 measures are the notes from middle C (linearly, in terms of note names) up to the C# that is two ledger lines above the treble clef.

26 happens to be the # of English letters in the English alphabet. Probably related.

I extracted the 4th note of each measure after the 26th measure, done line by line just in case the lines are somehow important:
F   B'	// 27,28
C   F#	// 29,30
G#' F#'	// 31,32
E   F	// 33,34
D'  G#'	// 35,36
F'  G'	// 37,38
G   C#'	// 39,40
D'  G'	// 41,42
E   D#'	// 43,44
E   F'	// 45,46
C'  E	// 47,48
C   F#'	// 49,50
G#' F'	// 51,52
E	// 53

Sorting into groups of 4 pitches (from the start, not from the end) because it's easy to convert to hex if it ends up being ASCII or just bytes-related:
F   B'	C   F#	// 27-30
G#' F#' E   F	// 31-34
D'  G#'	F'  G'	// 35-38
G   C#'	D'  G'	// 39-42
E   D#'	E   F'	// 43-46
C'  E	C   F#'	// 47-50
G#' F'	E	// 51-53


I see sharps in the 4th note names, so I know it's not 7TET that was used to encode data.
The next simplest thing to try would be assuming that the notes follow 12TET-style divisions per octave.
I'll treat note names as being relative to Middle C, because that seems like a reasonable starting/fundamental/ground/home note.

Let me make a Lookup Table to convert note names to numeric indices.

I'm going to make this table in terms of sensible-to-human octaves
* rather than Lilypond's "C and above (up to and including G) belong to same octave, but notes A to B belong to lower octave despite looking close to C".
* OneOctaveUp == <NOTE_NAME>'
+-----+------+---------------+---------------+
| Idx | Letr | Note_StartAtA | Note_StartAtC |
+-----+------+---------------+---------------+
| 1   | A    | A             | C             |
| 2   | B    | A#            | C#            |
| 3   | C    | B             | D             |
| 4   | D    | C             | D#            |
| 5   | E    | C#            | E             |
| 6   | F    | D             | F             |
| 7   | G    | D#            | F#            |
| 8   | H    | E             | G             |
| 9   | I    | F             | G#            |
| 10  | J    | F#            | A             |
| 11  | K    | G             | A#            |
| 12  | L    | G#            | B             |
| 13  | M    | A'            | C'            |
| 14  | N    | A#'           | C#'           |
| 15  | O    | B'            | D'            |
| 16  | P    | C'            | D#'           |
| 17  | Q    | C#'           | E'            |
| 18  | R    | D'            | F'            |
| 19  | S    | D#'           | F#'           |
| 20  | T    | E'            | G'            |
| 21  | U    | F'            | G#'           |
| 22  | V    | F#'           | A'            |
| 23  | W    | G'            | A#'           |
| 24  | X    | G#'           | B'            |
| 25  | Y    | A''           | C''           |
| 26  | Z    | A#''          | C#''          |
+-----+------+---------------+---------------+

I'm going to perform lookups to the integer indices first (and *then* map those indices to the notes), just in case there's a pattern in the numbers that I don't see in the notes, or in case I screwed up the table's mapping of the notes when creating the table.

F   B'	C   F#	// 27-30
-> IfBaseIsA: 9, 15, 4, 10 -> IODJ
-> IfBaseIsC: 6, 24, 1, 7  -> FXAG	// Looks close to FLAG... (just one letter off) Probably not using BaseNoteIsA then, so I'll stop wasting effort on that in the next rows.

G#' F#' E   F	// 31-34
-> IfBaseIsC: 21, 19, 5, 6 -> USEF

D'  G#'	F'  G'	// 35-38
-> IfBaseIsC: 15, 21, 18, 20 -> OURT

G   C#'	D'  G'	// 39-42
-> IfBaseIsC: 8, 14, 15, 20 -> HNOT

// These look kinda like gibberish. I'll concatenate the strings I have so far to see if they make any sense at all...
// [FXAG][USEF][OURT][HNOT] -> I guess "FLAG USE FOURTH NOT"? That sounds close enough to English to me to keep going down this path.

E   D#'	E   F'	// 43-46
-> IfBaseIsC: 5, 16, 5, 18 -> EPER

C'  E	C   F#'	// 47-50
-> IfBaseIsC: 13, 5, 1, 19 -> MEAS

G#' F'	E	// 51-53
-> IfBaseIsC: 21, 18, 5 -> URE

Concatenating all the note->index->EnglishLetter letters together into one string yields result:
* [FXAG][USEF][OURT][HNOT][EPER][MEAS][URE]
* FXAGUSEFOURTHNOTEPERMEASURE
// Let me change that X to an L to get FLAG and hope that the rest of the string is right:
* FLAG USE FOURTH NOTE PER MEASURE

Using that message at the top of the viewed-in-browser PDF:
* "'flag' keyword is included here, but not '{' nor '}'.  The extracted word is the flag."

I'll add curly braces to the flag, giving me one of the following:
* FLAG{USEFOURTHNOTEPERMEASURE}
* FLAG{USE FOURTH NOTE PER MEASURE}
* FLAG{USE_FOURTH_NOTE_PER_MEASURE}
* FLAG{use fourth note per measure}
* FLAG{use_fourth_note_per_measure}
* FLAG{usefourthnotepermeasure}
* Or a copy of all of the above possible flags, but where the copies' "FLAG" is lowercased to become "flag"


# Info - Reason behind obtaining `FXAG` instead of `FLAG`
* The reason that I got "FXAG" instead of "FLAG" is because the sheet music was generated with Lilypond, where octave notation centers around C instead of A.
  * In Lilypond, octaves aren't arranged like so: [ABCDEFG][A'B'C'D'E'F'G'][A''B''C''D''E''F''G''] but rather by [A,B,CDEFG][ABC'D'E'F'G'][A'B'C''D''E''F''G'']
<br>
<br>
<br>
<br>
<br>
<br>








# Time spent to solve this challenge

With knowing relatively quickly (for me, it was instantly) that I should pay attention to the fourth note of each measure, it took me, the creator of this challenge, **55 minutes** (including the slight help of AI to create that large Lookup table that I had already mostly made by hand) to solve this challenge.

Gemini Thinking3.6, solved this challenge in **1minute 19seconds** on 14 September 2026, in a new chat, when given the prompt "Solve this CTF Challenge." with me providing it the three files that are given to participants.
* I.e., Gemini solved this challenge 42.3x faster than me, the creator of this challenge.
* "3 filenames": Includes file "123FOUR_4ppc_7divRand_12divData.ly"
  * ***Due to multimodal LLM being able to solve the challenge only when provided that Lilycode file, and the Lilycode file not being necessary to solve the challenge, I will no longer provide that Lilycode file to the participants.***



# Appendix - Extra info about solving the challenge with multimodal LLMs
* Gemini Flash3.6 was too stupid to complete the table - it just jailbroke itself by leaking its own system prompt for some reason rather than doing the task of completing the table like I asked it to.
  * Gemini Thinking3.6 worked perfectly though when I asked it to complete the table.

When NOT provided with the lilycode file, even Gemini Pro3.1 failed to solve the challenge (after working on it for ~4-5 minutes), thinking that the creator's name that was inside the PDF, "StevieoXOR", was the hint to solving the challenge - using an XOR operation with some pseudorandom key (like the name "StevieoXOR") with every 4 bytes listed in the sheet music.
* Gemini Pro3.1 came across some options like Base64, Base32, XOR, moduloing by 7 and 12, dividing by 7 and 12, and even wrote a full script to parse the provided audio file into a MIDI integer representation for each note and then converted those integers directly into ASCII.


### Gemini Pro3.1's MIDI Parser function:
def parse_midi(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    
    idx = 0
    if data[idx:idx+4] != b'MThd':
        return "Not a valid MIDI"
    
    idx += 8 # skip length and MThd
    format_type = int.from_bytes(data[idx:idx+2], 'big')
    num_tracks = int.from_bytes(data[idx+2:idx+4], 'big')
    idx += 6
    
    notes = []
    for _ in range(num_tracks):
        if data[idx:idx+4] != b'MTrk':
            break
        trk_len = int.from_bytes(data[idx+4:idx+8], 'big')
        idx += 8
        end = idx + trk_len
        
        # very basic event parsing
        status = 0
        while idx < end:
            # read delta time (variable length)
            delta = 0
            while True:
                b = data[idx]
                idx += 1
                delta = (delta << 7) | (b & 0x7F)
                if not (b & 0x80):
                    break
            
            if idx >= end: break
            b = data[idx]
            if b & 0x80:
                status = b
                idx += 1
            
            # Note on/off
            if (status & 0xF0) in [0x90, 0x80]:
                note = data[idx]
                vel = data[idx+1]
                idx += 2
                if (status & 0xF0) == 0x90 and vel > 0:
                    notes.append(note)
            elif (status & 0xF0) in [0xA0, 0xB0, 0xE0]:
                idx += 2
            elif (status & 0xF0) in [0xC0, 0xD0]:
                idx += 1
            elif status == 0xFF:
                type_ = data[idx]
                idx += 1
                length = 0
                while True:
                    b = data[idx]
                    idx += 1
                    length = (length << 7) | (b & 0x7F)
                    if not (b & 0x80): break
                idx += length
    return notes

notes = parse_midi("123FOUR_4ppc_7divRand_12divData.mid")
print(notes)





# AI's Solution (when given all 3 files)
If you're curious, here's Gemini Thinking's entire written-out info of it providing its solution:
notes_raw = """
			% #0
			e'4           a'''          f'''          c'            
			
			% #1
			g''''         g'''          f'            cs'           
			
			% #2
			a''           g''''         e'''          d'            
			
			% #3
			b'            e''           a''           ds'           
			
			% #4
			g'            g''''         e''''         e'            
			
			% #5
			b''           f'''          f''           f'            
			
			% #6
			d'''          d''''         e''''         fs'           
			
			% #7
			f'''          c''           f''''         g'            
			
			% #8
			b'''          c'            b'''          gs'           
			
			% #9
			f''           b''           g'''          a'            
			
			% #10
			b'''          d''           e''''         as'           
			
			% #11
			a'            a'            b''           b'            
			
			% #12
			d'            b'''          b'            c''           
			
			% #13
			e''''         b'''          f'            cs''          
			
			% #14
			f''''         d''           c'''          d''           
			
			% #15
			e'            f''           g''''         ds''          
			
			% #16
			f''           f'''          c''''         e''           
			
			% #17
			e'''          d''           c'''          f''           
			
			% #18
			e''           e''           f''           fs''          
			
			% #19
			d'            f'            e''''         g''           
			
			% #20
			f'''          e'''          d'            gs''          
			
			% #21
			c''''         e'            g'''          a''           
			
			% #22
			d''''         e'            b'            as''          
			
			% #23
			a'            e''           c''''         b''           
			
			% #24
			c''''         d'            d''''         c'''          
			
			% #25
			e''           a'''          d''''         cs'''         
			
			% #26
			e'''          g'            c'''          f'            
			
			% #27
			f'''          b'            f'''          b'            
			
			% #28
			b''           g'            b'''          c'            
			
			% #29
			c''''         f''''         c'            fs'           
			
			% #30
			f'            a'''          g'            gs''          
			
			% #31
			a''''         b'''          b''           fs''          
			
			% #32
			e''           e'            e'            e'            
			
			% #33
			c''''         g''           f''           f'            
			
			% #34
			e''           d'''          e''           d''           
			
			% #35
			d''           f'            c'            gs''          
			
			% #36
			a''''         c'''          d'''          f''           
			
			% #37
			e''           c'            e''''         g''           
			
			% #38
			c'            d''           a'            g'            
			
			% #39
			f''''         f'''          d''           cs''          
			
			% #40
			a'''          g''''         a'''          d''           
			
			% #41
			c''           f''           d''''         g''           
			
			% #42
			c'            e''           g''''         e'            
			
			% #43
			b''           a''''         d''           ds''          
			
			% #44
			e''           f'''          f'            e'            
			
			% #45
			g'''          g'''          e''           f''           
			
			% #46
			f''''         b''           b'            c''           
			
			% #47
			f''''         a'''          g'''          e'            
			
			% #48
			b'''          a'            d''           c'            
			
			% #49
			g'''          b'            c'            fs''          
			
			% #50
			d''           b'''          f''''         gs''          
			
			% #51
			f''''         d''           e'            f''           
			
			% #52
			b''           c''''         f''''         e'            
"""

import re

# Clean and extract notes
lines = [l.strip() for l in notes_raw.split('\n') if l.strip() and not l.strip().startswith('%')]
notes = []
for l in lines:
    tokens = l.split()
    for t in tokens:
        # strip duration if present (like 4 in e'4)
        t_clean = re.sub(r'\d+', '', t)
        notes.append(t_clean)

print(f"Total notes count: {len(notes)}")
print(f"Measures / blocks count: {len(notes)//4}")
print("First 12 notes:", notes[:12])



Code output
Total notes count: 212
Measures / blocks count: 53
First 12 notes: ["e'", "a'''", "f'''", "c'", "g''''", "g'''", "f'", "cs'", "a''", "g''''", "e'''", "d'"]




# END GEMINI CODE BLOCK 1
# START GEMINI CODE BLOCK 2





# Pitch class map (C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11)
pitch_class = {
    'c': 0, 'cs': 1, 'df': 1, 'd': 2, 'ds': 3, 'ef': 3, 'e': 4,
    'f': 5, 'fs': 6, 'gf': 6, 'g': 7, 'gs': 8, 'af': 8, 'a': 9, 'as': 10, 'bf': 10, 'b': 11
}

def parse_note(note_str):
    # Base note name (e.g. cs, e, a, ds, as)
    base = re.match(r'([a-g][sf]?)', note_str).group(1)
    # Octave marks: ' means +1 octave, , means -1 octave
    octave_ticks = note_str[len(base):]
    octave_offset = octave_ticks.count("'") - octave_ticks.count(",")
    
    # Absolute MIDI pitch or semitone index (assuming c' = 60 or reference 0)
    semitones = pitch_class[base] + 12 * octave_offset
    return base, octave_offset, semitones, pitch_class[base]

parsed_notes = [parse_note(n) for n in notes]

# Group by measure (4 notes each)
for i in range(10):
    m = parsed_notes[i*4 : (i+1)*4]
    print(f"Measure #{i}:")
    for j, (base, oct_off, semi, pc) in enumerate(m):
        print(f"  Note {j}: name={notes[i*4+j]}, base={base}, oct={oct_off}, semi={semi}, pc={pc}")


Code output
Measure #0:
  Note 0: name=e', base=e, oct=1, semi=16, pc=4
  Note 1: name=a''', base=a, oct=3, semi=45, pc=9
  Note 2: name=f''', base=f, oct=3, semi=41, pc=5
  Note 3: name=c', base=c, oct=1, semi=12, pc=0
Measure #1:
  Note 0: name=g'''', base=g, oct=4, semi=55, pc=7
  Note 1: name=g''', base=g, oct=3, semi=43, pc=7
  Note 2: name=f', base=f, oct=1, semi=17, pc=5
  Note 3: name=cs', base=cs, oct=1, semi=13, pc=1
Measure #2:
  Note 0: name=a'', base=a, oct=2, semi=33, pc=9
  Note 1: name=g'''', base=g, oct=4, semi=55, pc=7
  Note 2: name=e''', base=e, oct=3, semi=40, pc=4
  Note 3: name=d', base=d, oct=1, semi=14, pc=2
Measure #3:
  Note 0: name=b', base=b, oct=1, semi=23, pc=11
  Note 1: name=e'', base=e, oct=2, semi=28, pc=4
  Note 2: name=a'', base=a, oct=2, semi=33, pc=9
  Note 3: name=ds', base=ds, oct=1, semi=15, pc=3
Measure #4:
  Note 0: name=g', base=g, oct=1, semi=19, pc=7
  Note 1: name=g'''', base=g, oct=4, semi=55, pc=7
  Note 2: name=e'''', base=e, oct=4, semi=52, pc=4
  Note 3: name=e', base=e, oct=1, semi=16, pc=4
Measure #5:
  Note 0: name=b'', base=b, oct=2, semi=35, pc=11
  Note 1: name=f''', base=f, oct=3, semi=41, pc=5
  Note 2: name=f'', base=f, oct=2, semi=29, pc=5
  Note 3: name=f', base=f, oct=1, semi=17, pc=5
Measure #6:
  Note 0: name=d''', base=d, oct=3, semi=38, pc=2
  Note 1: name=d'''', base=d, oct=4, semi=50, pc=2
  Note 2: name=e'''', base=e, oct=4, semi=52, pc=4
  Note 3: name=fs', base=fs, oct=1, semi=18, pc=6
Measure #7:
  Note 0: name=f''', base=f, oct=3, semi=41, pc=5
  Note 1: name=c'', base=c, oct=2, semi=24, pc=0
  Note 2: name=f'''', base=f, oct=4, semi=53, pc=5
  Note 3: name=g', base=g, oct=1, semi=19, pc=7
Measure #8:
  Note 0: name=b''', base=b, oct=3, semi=47, pc=11
  Note 1: name=c', base=c, oct=1, semi=12, pc=0
  Note 2: name=b''', base=b, oct=3, semi=47, pc=11
  Note 3: name=gs', base=gs, oct=1, semi=20, pc=8
Measure #9:
  Note 0: name=f'', base=f, oct=2, semi=29, pc=5
  Note 1: name=b'', base=b, oct=2, semi=35, pc=11
  Note 2: name=g''', base=g, oct=3, semi=43, pc=7
  Note 3: name=a', base=a, oct=1, semi=21, pc=9







# END GEMINI CODE BLOCK 2
# START GEMINI CODE BLOCK 3






fourth_notes = [notes[i*4 + 3] for i in range(53)]
print("Fourth notes in each measure:")
for i, n in enumerate(fourth_notes):
    print(f"#{i}: {n}", end=", ")
    if (i+1)%8 == 0: print()
print()


Code output
Fourth notes in each measure:
#0: c', #1: cs', #2: d', #3: ds', #4: e', #5: f', #6: fs', #7: g', 
#8: gs', #9: a', #10: as', #11: b', #12: c'', #13: cs'', #14: d'', #15: ds'', 
#16: e'', #17: f'', #18: fs'', #19: g'', #20: gs'', #21: a'', #22: as'', #23: b'', 
#24: c''', #25: cs''', #26: f', #27: b', #28: c', #29: fs', #30: gs'', #31: fs'', 
#32: e', #33: f', #34: d'', #35: gs'', #36: f'', #37: g'', #38: g', #39: cs'', 
#40: d'', #41: g'', #42: e', #43: ds'', #44: e', #45: f'', #46: c'', #47: e', 
#48: c', #49: fs'', #50: gs'', #51: f'', #52: e',




# END GEMINI CODE BLOCK 3
# START GEMINI CODE BLOCK 4




# Let's print all 4 notes for each measure from 0 to 52 in detail
chromatic_scale = ['c', 'cs', 'd', 'ds', 'e', 'f', 'fs', 'g', 'gs', 'a', 'as', 'b']

def note_to_chromatic_index(note_str):
    # Parse note_str into chromatic offset from c'
    base = re.match(r'([a-g][sf]?)', note_str).group(1)
    ticks = note_str[len(base):]
    octave = ticks.count("'") - ticks.count(",")
    pc = pitch_class[base]
    # c' is octave=1, pc=0 -> index 0
    # Let's set c' = 0
    index = (octave - 1) * 12 + pc
    return index

for i in range(53):
    m = [notes[i*4 + j] for j in range(4)]
    indices = [note_to_chromatic_index(n) for n in m]
    print(f"Measure #{i:2d}: notes = {m}, chromatic_indices = {indices}")



Code output
Measure # 0: notes = ["e'", "a'''", "f'''", "c'"], chromatic_indices = [4, 33, 29, 0]
Measure # 1: notes = ["g''''", "g'''", "f'", "cs'"], chromatic_indices = [43, 31, 5, 1]
Measure # 2: notes = ["a''", "g''''", "e'''", "d'"], chromatic_indices = [21, 43, 28, 2]
Measure # 3: notes = ["b'", "e''", "a''", "ds'"], chromatic_indices = [11, 16, 21, 3]
Measure # 4: notes = ["g'", "g''''", "e''''", "e'"], chromatic_indices = [7, 43, 40, 4]
Measure # 5: notes = ["b''", "f'''", "f''", "f'"], chromatic_indices = [23, 29, 17, 5]
Measure # 6: notes = ["d'''", "d''''", "e''''", "fs'"], chromatic_indices = [26, 38, 40, 6]
Measure # 7: notes = ["f'''", "c''", "f''''", "g'"], chromatic_indices = [29, 12, 41, 7]
Measure # 8: notes = ["b'''", "c'", "b'''", "gs'"], chromatic_indices = [35, 0, 35, 8]
Measure # 9: notes = ["f''", "b''", "g'''", "a'"], chromatic_indices = [17, 23, 31, 9]
Measure #10: notes = ["b'''", "d''", "e''''", "as'"], chromatic_indices = [35, 14, 40, 10]
Measure #11: notes = ["a'", "a'", "b''", "b'"], chromatic_indices = [9, 9, 23, 11]
Measure #12: notes = ["d'", "b'''", "b'", "c''"], chromatic_indices = [2, 35, 11, 12]
Measure #13: notes = ["e''''", "b'''", "f'", "cs''"], chromatic_indices = [40, 35, 5, 13]
Measure #14: notes = ["f''''", "d''", "c'''", "d''"], chromatic_indices = [41, 14, 24, 14]
Measure #15: notes = ["e'", "f''", "g''''", "ds''"], chromatic_indices = [4, 17, 43, 15]
Measure #16: notes = ["f''", "f'''", "c''''", "e''"], chromatic_indices = [17, 29, 36, 16]
Measure #17: notes = ["e'''", "d''", "c'''", "f''"], chromatic_indices = [28, 14, 24, 17]
Measure #18: notes = ["e''", "e''", "f''", "fs''"], chromatic_indices = [16, 16, 17, 18]
Measure #19: notes = ["d'", "f'", "e''''", "g''"], chromatic_indices = [2, 5, 40, 19]
Measure #20: notes = ["f'''", "e'''", "d'", "gs''"], chromatic_indices = [29, 28, 2, 20]
Measure #21: notes = ["c''''", "e'", "g'''", "a''"], chromatic_indices = [36, 4, 31, 21]
Measure #22: notes = ["d''''", "e'", "b'", "as''"], chromatic_indices = [38, 4, 11, 22]
Measure #23: notes = ["a'", "e''", "c''''", "b''"], chromatic_indices = [9, 16, 36, 23]
Measure #24: notes = ["c''''", "d'", "d''''", "c'''"], chromatic_indices = [36, 2, 38, 24]
Measure #25: notes = ["e''", "a'''", "d''''", "cs'''"], chromatic_indices = [16, 33, 38, 25]
Measure #26: notes = ["e'''", "g'", "c'''", "f'"], chromatic_indices = [28, 7, 24, 5]
Measure #27: notes = ["f'''", "b'", "f'''", "b'"], chromatic_indices = [29, 11, 29, 11]
Measure #28: notes = ["b''", "g'", "b'''", "c'"], chromatic_indices = [23, 7, 35, 0]
Measure #29: notes = ["c''''", "f''''", "c'", "fs'"], chromatic_indices = [36, 41, 0, 6]
Measure #30: notes = ["f'", "a'''", "g'", "gs''"], chromatic_indices = [5, 33, 7, 20]
Measure #31: notes = ["a''''", "b'''", "b''", "fs''"], chromatic_indices = [45, 35, 23, 18]
Measure #32: notes = ["e''", "e'", "e'", "e'"], chromatic_indices = [16, 4, 4, 4]
Measure #33: notes = ["c''''", "g''", "f''", "f'"], chromatic_indices = [36, 19, 17, 5]
Measure #34: notes = ["e''", "d'''", "e''", "d''"], chromatic_indices = [16, 26, 16, 14]
Measure #35: notes = ["d''", "f'", "c'", "gs''"], chromatic_indices = [14, 5, 0, 20]
Measure #36: notes = ["a''''", "c'''", "d'''", "f''"], chromatic_indices = [45, 24, 26, 17]
Measure #37: notes = ["e''", "c'", "e''''", "g''"], chromatic_indices = [16, 0, 40, 19]
Measure #38: notes = ["c'", "d''", "a'", "g'"], chromatic_indices = [0, 14, 9, 7]
Measure #39: notes = ["f''''", "f'''", "d''", "cs''"], chromatic_indices = [41, 29, 14, 13]
Measure #40: notes = ["a'''", "g''''", "a'''", "d''"], chromatic_indices = [33, 43, 33, 14]
Measure #41: notes = ["c''", "f''", "d''''", "g''"], chromatic_indices = [12, 17, 38, 19]
Measure #42: notes = ["c'", "e''", "g''''", "e'"], chromatic_indices = [0, 16, 43, 4]
Measure #43: notes = ["b''", "a''''", "d''", "ds''"], chromatic_indices = [23, 45, 14, 15]
Measure #44: notes = ["e''", "f'''", "f'", "e'"], chromatic_indices = [16, 29, 5, 4]
Measure #45: notes = ["g'''", "g'''", "e''", "f''"], chromatic_indices = [31, 31, 16, 17]
Measure #46: notes = ["f''''", "b''", "b'", "c''"], chromatic_indices = [41, 23, 11, 12]
Measure #47: notes = ["f''''", "a'''", "g'''", "e'"], chromatic_indices = [41, 33, 31, 4]
Measure #48: notes = ["b'''", "a'", "d''", "c'"], chromatic_indices = [35, 9, 14, 0]
Measure #49: notes = ["g'''", "b'", "c'", "fs''"], chromatic_indices = [31, 11, 0, 18]
Measure #50: notes = ["d''", "b'''", "f''''", "gs''"], chromatic_indices = [14, 35, 41, 20]
Measure #51: notes = ["f''''", "d''", "e'", "f''"], chromatic_indices = [41, 14, 4, 17]
Measure #52: notes = ["b''", "c''''", "f''''", "e'"], chromatic_indices = [23, 36, 41, 4]








# END GEMINI CODE BLOCK 4
# START GEMINI CODE BLOCK 5






# Let's inspect the 4 chromatic indices for measures 0..25 and 26..52
m_0_25 = [ [note_to_chromatic_index(notes[i*4+j]) for j in range(4)] for i in range(26) ]
m_26_52 = [ [note_to_chromatic_index(notes[i*4+j]) for j in range(4)] for i in range(26, 53) ]

print("Measures 0..25:")
for i, m in enumerate(m_0_25):
    print(f"{chr(65+i)} (m#{i:2d}): {m}")

print("\nMeasures 26..52:")
for i, m in enumerate(m_26_52):
    print(f"Char #{i:2d} (m#{i+26:2d}): {m}")


Code output
Measures 0..25:
A (m# 0): [4, 33, 29, 0]
B (m# 1): [43, 31, 5, 1]
C (m# 2): [21, 43, 28, 2]
D (m# 3): [11, 16, 21, 3]
E (m# 4): [7, 43, 40, 4]
F (m# 5): [23, 29, 17, 5]
G (m# 6): [26, 38, 40, 6]
H (m# 7): [29, 12, 41, 7]
I (m# 8): [35, 0, 35, 8]
J (m# 9): [17, 23, 31, 9]
K (m#10): [35, 14, 40, 10]
L (m#11): [9, 9, 23, 11]
M (m#12): [2, 35, 11, 12]
N (m#13): [40, 35, 5, 13]
O (m#14): [41, 14, 24, 14]
P (m#15): [4, 17, 43, 15]
Q (m#16): [17, 29, 36, 16]
R (m#17): [28, 14, 24, 17]
S (m#18): [16, 16, 17, 18]
T (m#19): [2, 5, 40, 19]
U (m#20): [29, 28, 2, 20]
V (m#21): [36, 4, 31, 21]
W (m#22): [38, 4, 11, 22]
X (m#23): [9, 16, 36, 23]
Y (m#24): [36, 2, 38, 24]
Z (m#25): [16, 33, 38, 25]

Measures 26..52:
Char # 0 (m#26): [28, 7, 24, 5]
Char # 1 (m#27): [29, 11, 29, 11]
Char # 2 (m#28): [23, 7, 35, 0]
Char # 3 (m#29): [36, 41, 0, 6]
Char # 4 (m#30): [5, 33, 7, 20]
Char # 5 (m#31): [45, 35, 23, 18]
Char # 6 (m#32): [16, 4, 4, 4]
Char # 7 (m#33): [36, 19, 17, 5]
Char # 8 (m#34): [16, 26, 16, 14]
Char # 9 (m#35): [14, 5, 0, 20]
Char #10 (m#36): [45, 24, 26, 17]
Char #11 (m#37): [16, 0, 40, 19]
Char #12 (m#38): [0, 14, 9, 7]
Char #13 (m#39): [41, 29, 14, 13]
Char #14 (m#40): [33, 43, 33, 14]
Char #15 (m#41): [12, 17, 38, 19]
Char #16 (m#42): [0, 16, 43, 4]
Char #17 (m#43): [23, 45, 14, 15]
Char #18 (m#44): [16, 29, 5, 4]
Char #19 (m#45): [31, 31, 16, 17]
Char #20 (m#46): [41, 23, 11, 12]
Char #21 (m#47): [41, 33, 31, 4]
Char #22 (m#48): [35, 9, 14, 0]
Char #23 (m#49): [31, 11, 0, 18]
Char #24 (m#50): [14, 35, 41, 20]
Char #25 (m#51): [41, 14, 4, 17]






# END GEMINI CODE BLOCK 5
# START GEMINI CODE BLOCK 6




msg = "".join([chr(65 + m_26_52[i][3]) for i in range(27)])
print("Extracted 4th notes (measures 26..52):")
print(msg)

# What about 1st, 2nd, 3rd notes?
msg_0 = "".join([chr(65 + m_26_52[i][0] % 26) for i in range(27)])
msg_1 = "".join([chr(65 + m_26_52[i][1] % 26) for i in range(27)])
msg_2 = "".join([chr(65 + m_26_52[i][2] % 26) for i in range(27)])

print("1st notes mod 26:", msg_0)
print("2nd notes mod 26:", msg_1)
print("3rd notes mod 26:", msg_2)


Code output
Extracted 4th notes (measures 26..52):
FLAGUSEFOURTHNOTEPERMEASURE
1st notes mod 26: CDXKFTQKQOTQAPHMAXQFPPJFOPX
2nd notes mod 26: HLHPHJETAFYAODRRQTDFXHJLJOK
3rd notes mod 26: YDJAHXERQAAOJOHMROFQLFOAPEP



# END GEMINI CODE BLOCK 6

