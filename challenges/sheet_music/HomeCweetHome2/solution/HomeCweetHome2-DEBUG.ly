
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
	title     = "Home Cweet Home 2"
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
			\sectionLabel "Section24"
			% Original text: ABCDEFGHIJKLMNOPQRSTUVWXYZFLAGDISTANCEFROMTHELETTERABELOWMIDDLEC
			% Intermediate text: [['A,0'], ['B,1'], ['C,2'], ['D,3'], ['E,4'], ['F,5'], ['G,6'], ['H,7'], ['I,8'], ['J,9'], ['K,10'], ['L,11'], ['M,12'], ['N,13'], ['O,14'], ['P,15'], ['Q,16'], ['R,17'], ['S,18'], ['T,19'], ['U,20'], ['V,21'], ['W,22'], ['X,23'], ['Y,24'], ['Z,25'], ['F,5'], ['L,11'], ['A,0'], ['G,6'], ['D,3'], ['I,8'], ['S,18'], ['T,19'], ['A,0'], ['N,13'], ['C,2'], ['E,4'], ['F,5'], ['R,17'], ['O,14'], ['M,12'], ['T,19'], ['H,7'], ['E,4'], ['L,11'], ['E,4'], ['T,19'], ['T,19'], ['E,4'], ['R,17'], ['A,0'], ['B,1'], ['E,4'], ['L,11'], ['O,14'], ['W,22'], ['M,12'], ['I,8'], ['D,3'], ['D,3'], ['L,11'], ['E,4'], ['C,2']]
			% Below notes created using 24 divisions of an octave and [a] as a reference pitch

			% Char #0
			<>^"origA,intrmed0" a4  
			% Char #1
			<>^"origB,intrmed1" aqs  
			% Char #2
			<>^"origC,intrmed2" as  
			% Char #3
			<>^"origD,intrmed3" atqs  
			
			% Char #4
			<>^"origE,intrmed4" b  
			% Char #5
			<>^"origF,intrmed5" bqs  
			% Char #6
			<>^"origG,intrmed6" c'  
			% Char #7
			<>^"origH,intrmed7" cqs'  
			\break
			
			
			% Char #8
			<>^"origI,intrmed8" cs'  
			% Char #9
			<>^"origJ,intrmed9" ctqs'  
			% Char #10
			<>^"origK,intrmed10" d'  
			% Char #11
			<>^"origL,intrmed11" dqs'  
			
			% Char #12
			<>^"origM,intrmed12" ds'  
			% Char #13
			<>^"origN,intrmed13" dtqs'  
			% Char #14
			<>^"origO,intrmed14" e'  
			% Char #15
			<>^"origP,intrmed15" eqs'  
			\break
			
			
			% Char #16
			<>^"origQ,intrmed16" f'  
			% Char #17
			<>^"origR,intrmed17" fqs'  
			% Char #18
			<>^"origS,intrmed18" fs'  
			% Char #19
			<>^"origT,intrmed19" ftqs'  
			
			% Char #20
			<>^"origU,intrmed20" g'  
			% Char #21
			<>^"origV,intrmed21" gqs'  
			% Char #22
			<>^"origW,intrmed22" gs'  
			% Char #23
			<>^"origX,intrmed23" gtqs'  
			\break
			
			
			% Char #24
			<>^"origY,intrmed24" a'  
			% Char #25
			<>^"origZ,intrmed25" aqs'  
			% Char #26
			<>^"origF,intrmed5" bqs  
			% Char #27
			<>^"origL,intrmed11" dqs'  
			
			% Char #28
			<>^"origA,intrmed0" a  
			% Char #29
			<>^"origG,intrmed6" c'  
			% Char #30
			<>^"origD,intrmed3" atqs  
			% Char #31
			<>^"origI,intrmed8" cs'  
			\break
			
			
			% Char #32
			<>^"origS,intrmed18" fs'  
			% Char #33
			<>^"origT,intrmed19" ftqs'  
			% Char #34
			<>^"origA,intrmed0" a  
			% Char #35
			<>^"origN,intrmed13" dtqs'  
			
			% Char #36
			<>^"origC,intrmed2" as  
			% Char #37
			<>^"origE,intrmed4" b  
			% Char #38
			<>^"origF,intrmed5" bqs  
			% Char #39
			<>^"origR,intrmed17" fqs'  
			\break
			
			
			% Char #40
			<>^"origO,intrmed14" e'  
			% Char #41
			<>^"origM,intrmed12" ds'  
			% Char #42
			<>^"origT,intrmed19" ftqs'  
			% Char #43
			<>^"origH,intrmed7" cqs'  
			
			% Char #44
			<>^"origE,intrmed4" b  
			% Char #45
			<>^"origL,intrmed11" dqs'  
			% Char #46
			<>^"origE,intrmed4" b  
			% Char #47
			<>^"origT,intrmed19" ftqs'  
			\break
			
			
			% Char #48
			<>^"origT,intrmed19" ftqs'  
			% Char #49
			<>^"origE,intrmed4" b  
			% Char #50
			<>^"origR,intrmed17" fqs'  
			% Char #51
			<>^"origA,intrmed0" a  
			
			% Char #52
			<>^"origB,intrmed1" aqs  
			% Char #53
			<>^"origE,intrmed4" b  
			% Char #54
			<>^"origL,intrmed11" dqs'  
			% Char #55
			<>^"origO,intrmed14" e'  
			\break
			
			
			% Char #56
			<>^"origW,intrmed22" gs'  
			% Char #57
			<>^"origM,intrmed12" ds'  
			% Char #58
			<>^"origI,intrmed8" cs'  
			% Char #59
			<>^"origD,intrmed3" atqs  
			
			% Char #60
			<>^"origD,intrmed3" atqs  
			% Char #61
			<>^"origL,intrmed11" dqs'  
			% Char #62
			<>^"origE,intrmed4" b  
			% Char #63
			<>^"origC,intrmed2" as  
			\break
			
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


