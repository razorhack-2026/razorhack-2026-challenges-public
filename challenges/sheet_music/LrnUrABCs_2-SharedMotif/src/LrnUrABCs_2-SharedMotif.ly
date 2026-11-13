
% Lilypond version
\version "2.26.0"

% Language of note-names, sharps, flats, etc
\language "english"

% Top of page
\header {
	title     = "Learn Your 7 (or 12) ABCs #2 - Shared Motif"
	subtitle  = "'flag{', '}' keywords not included here.  The extracted word is the flag."
	composer  = "StevieoXOR"
	copyright = "Copyright is CopyLeft"
}



myString = {b4 a g d a d}
myStringWRest = {\myString r4 r\fermata}


sectionSimplest = {\myStringWRest |}

sectionRepeat = \repeat "volta" 2 {\myStringWRest | }

sectionQuadVoice =
	<<
		\relative c    {\myString    } \\
		\relative c'   {\myStringWRest |} \\
		\relative c''  {\myString    } \\
		\relative c''' {\myString    }
	>>

sectionDichords =
	\relative c' {
		<b a>4
		<a' g>
		<g d>
		<d a>
		<a d>
		<d b>
		r
		r\fermata |
	}

sectionV =
	\relative c''{
		<b b'>4
		<<a \\ {g8 fs}>>
		<g d(>4
		<d g)>
		<<{a8[ b8]} \\ {e4}>>
		<d c>
		r2\fermata |
	}


sectionVI = 
	\relative c'' {
		\textMark "Maj7 chords"
		\chordmode {b4:maj7 a:maj7 g:maj7 d:maj7 a:maj7 d:maj7} r\fermata
		
		\textMark "Maj(5) chords"
		\chordmode {b4 a g' d,, a d} r\fermata
		
		\textMark "Aug chords"
		\chordmode {b4:aug a:aug g:aug d':aug a,:aug d:aug} r\fermata
		
		\textMark "Min chords"
		\chordmode {b4:m a:m g:m d:m a:m d:m} r\fermata
		
		\textMark "Dim chords"
		\chordmode {b4:dim a:dim g:dim d:dim a:dim d:dim} r\fermata
		
		\textMark "Differing-Degree chords"
		\chordmode {
			b4:2 a:3 g:4 d:5
			a:6 d:7 r r %%|
			b:8 a:9 g:10 d:11
			a:12 d:13 r r %%|
		}
	}

sectionTransposed=
	\transpose c g'
	{b4 a g d a d}



\score {
	\relative c''{
		\key c \major
		\numericTimeSignature
			\time 8/4
		\tempo 4=120	%Quarter(4) note = 120bpm
		
		\sectionLabel "Sec1"
		\sectionSimplest
		
		\sectionLabel "Sec2"
		\sectionRepeat
		
		\sectionLabel "Sec3"
		\sectionQuadVoice
		\break
		
		
		\sectionLabel "Sec4"
		\sectionDichords
		
		\sectionLabel "Sec5"
		\sectionV
		\bar "|."
		\break
		
		
		\sectionLabel "Sec6"
		\sectionVI
		\break
		
		\sectionLabel "Transposed"
		\sectionTransposed
		
		
	}
	\layout{}
	\midi{}
}

