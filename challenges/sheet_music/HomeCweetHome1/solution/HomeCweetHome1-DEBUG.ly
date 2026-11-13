
% To compile this Lilypond file into sheet music and/or an audio file,
%   you should create a PATH Environment variable referencing the LilyPond program you already installed in Frescobaldi
%   at C:\Users\<YOUR USERNAME>\AppData\Local\frescobaldi\frescobaldi\lilypond-binaries\lilypond-2.26.0\bin
%  * Your version number may differ from 2.26.0

% This program assumes you have already
%  1) Installed Frescobaldi,
%  2) Downloaded and installed LilyPond via Frescobaldi
%     (not via a separate browser download, but rather by opening Frescobaldi->"Edit" on its top toolbar->Preferences->Lilypond->+Add...->Click the most up-to-date version->Wait for the download. Ignore the "LilyPond include path" section, leaving it empty.

% Lilypond version
\version "2.26.0"

% Language of note-names, sharps, flats, etc
\language "english"

% Top of page
\header {
	title     = "Home Cweet Home 1"
	subtitle  = "'flag' keyword is included here, but not '{' nor '}'.  The extracted word is the flag."

	composer  = "Mort"
	copyright = "Copyright is CopyLeft"
}

% NOT USING RELATIVE-PITCH NOTATION. USING ABSOLUTE PITCHES.
\score{
	% --------------- OVERALL PROCESS ---------------
	% Secret string to encode into sheet music -> list(EnglishLetter)
	% -> LetterToNumber -> FindOctvDivisionScale -> ToRelativeMusicNotePitch -> ToAbsoluteMusicNotePitch
	% -> AddMusicMetadata__TimeSignature_Tempo_NoteDuration
	% -----------------------------------------------

	% Music-related info
	{
		\key c \major
		\numericTimeSignature
			\time 4/4
		\tempo 4=120	% Quarter(4) note = 120bpm

		% Actual music notes go below, followed by a closing '}'
		\absolute{
			% !!!!!!!!!!!!!!!!!!!!
			% !!!  DEBUG MODE  !!!
			% !!!!!!!!!!!!!!!!!!!!
			\sectionLabel "Section12"
			% Original text: ABCDEFGHIJKLMNOPQRSTUVWXYZFLAGDISTANCEFROMMIDDLEC
			% Intermediate text: [['A,0'], ['B,1'], ['C,2'], ['D,3'], ['E,4'], ['F,5'], ['G,6'], ['H,7'], ['I,8'], ['J,9'], ['K,10'], ['L,11'], ['M,12'], ['N,13'], ['O,14'], ['P,15'], ['Q,16'], ['R,17'], ['S,18'], ['T,19'], ['U,20'], ['V,21'], ['W,22'], ['X,23'], ['Y,24'], ['Z,25'], ['F,5'], ['L,11'], ['A,0'], ['G,6'], ['D,3'], ['I,8'], ['S,18'], ['T,19'], ['A,0'], ['N,13'], ['C,2'], ['E,4'], ['F,5'], ['R,17'], ['O,14'], ['M,12'], ['M,12'], ['I,8'], ['D,3'], ['D,3'], ['L,11'], ['E,4'], ['C,2']]
			% Below notes created using 12 divisions of an octave and [c] as a reference pitch

			% Char #0
			<>^"origA,intrmed0" c'4  
			% Char #1
			<>^"origB,intrmed1" cs'  
			% Char #2
			<>^"origC,intrmed2" d'  
			% Char #3
			<>^"origD,intrmed3" ds'  
			
			% Char #4
			<>^"origE,intrmed4" e'  
			% Char #5
			<>^"origF,intrmed5" f'  
			% Char #6
			<>^"origG,intrmed6" fs'  
			% Char #7
			<>^"origH,intrmed7" g'  
			\break
			
			
			% Char #8
			<>^"origI,intrmed8" gs'  
			% Char #9
			<>^"origJ,intrmed9" a'  
			% Char #10
			<>^"origK,intrmed10" as'  
			% Char #11
			<>^"origL,intrmed11" b'  
			
			% Char #12
			<>^"origM,intrmed12" c''  
			% Char #13
			<>^"origN,intrmed13" cs''  
			% Char #14
			<>^"origO,intrmed14" d''  
			% Char #15
			<>^"origP,intrmed15" ds''  
			\break
			
			
			% Char #16
			<>^"origQ,intrmed16" e''  
			% Char #17
			<>^"origR,intrmed17" f''  
			% Char #18
			<>^"origS,intrmed18" fs''  
			% Char #19
			<>^"origT,intrmed19" g''  
			
			% Char #20
			<>^"origU,intrmed20" gs''  
			% Char #21
			<>^"origV,intrmed21" a''  
			% Char #22
			<>^"origW,intrmed22" as''  
			% Char #23
			<>^"origX,intrmed23" b''  
			\break
			
			
			% Char #24
			<>^"origY,intrmed24" c'''  
			% Char #25
			<>^"origZ,intrmed25" cs'''  
			% Char #26
			<>^"origF,intrmed5" f'  
			% Char #27
			<>^"origL,intrmed11" b'  
			
			% Char #28
			<>^"origA,intrmed0" c'  
			% Char #29
			<>^"origG,intrmed6" fs'  
			% Char #30
			<>^"origD,intrmed3" ds'  
			% Char #31
			<>^"origI,intrmed8" gs'  
			\break
			
			
			% Char #32
			<>^"origS,intrmed18" fs''  
			% Char #33
			<>^"origT,intrmed19" g''  
			% Char #34
			<>^"origA,intrmed0" c'  
			% Char #35
			<>^"origN,intrmed13" cs''  
			
			% Char #36
			<>^"origC,intrmed2" d'  
			% Char #37
			<>^"origE,intrmed4" e'  
			% Char #38
			<>^"origF,intrmed5" f'  
			% Char #39
			<>^"origR,intrmed17" f''  
			\break
			
			
			% Char #40
			<>^"origO,intrmed14" d''  
			% Char #41
			<>^"origM,intrmed12" c''  
			% Char #42
			<>^"origM,intrmed12" c''  
			% Char #43
			<>^"origI,intrmed8" gs'  
			
			% Char #44
			<>^"origD,intrmed3" ds'  
			% Char #45
			<>^"origD,intrmed3" ds'  
			% Char #46
			<>^"origL,intrmed11" b'  
			% Char #47
			<>^"origE,intrmed4" e'  
			\break
			
			
			% Char #48
			<>^"origC,intrmed2" d'  
		}
	}

	% SheetMusic layout info
	\layout{}

	% Audible playback info (I have never needed to put anything in this)
	\midi{}
}
%%%%%%%%%%%%%%%%%%%%
%%%%% END FILE %%%%%
%%%%%%%%%%%%%%%%%%%%


