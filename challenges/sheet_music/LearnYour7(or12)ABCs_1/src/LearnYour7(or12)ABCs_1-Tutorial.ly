
% Lilypond version
\version "2.26.0"

% Language of note-names, sharps, flats, etc
\language "english"

% Top of page
\header {
	title     = "LearnYour7(or12)ABCs #1 - Tutorial"
	subtitle  = "'flag{', '}' keywords not included here.  The extracted word is the flag."
	composer  = "StevieoXOR"
	copyright = "Copyright is CopyLeft"
}



myString = {c4 a b b a g e}
myStringWRest = {\myString r\fermata}


sectionSimplest = {\myStringWRest |}

sectionRepeat = \repeat "volta" 2 {\myStringWRest | }

sectionTransposed=
	\transpose c g'	% from c, to g'
	{c4 a b b a g e}



\score {
	\relative c''{
		\key c \major
		\numericTimeSignature
			\time 8/4
		\tempo 4=120	%Quarter(4) note = 120bpm
		
		\sectionLabel "Motif"
		\sectionSimplest
		
		\sectionLabel "ShiftedDownByOctave"
		\sectionRepeat
		\break
		
		\sectionLabel "Transposed"
		\sectionTransposed
		
		
	}
	\layout{}
	\midi{}
}

