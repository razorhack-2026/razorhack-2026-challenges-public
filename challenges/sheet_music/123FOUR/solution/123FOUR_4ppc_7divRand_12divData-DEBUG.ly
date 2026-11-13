
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
	title     = "1 2 3 FOUR"
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
		\tempo 4=240	% Quarter(4) note = 240bpm

		% Actual music notes go below, followed by a closing '}'
		\absolute{
			% !!!!!!!!!!!!!!!!!!!!
			% !!!  DEBUG MODE  !!!
			% !!!!!!!!!!!!!!!!!!!!
			\sectionLabel "Section12"
			% Original text: ABCDEFGHIJKLMNOPQRSTUVWXYZFLAGUSEFOURTHNOTEPERMEASURE
			% Intermediate text: [['A,0[1/4]', 'A,0[2/4]', 'A,0[3/4]', 'A,0[4/4]'], ['B,1[1/4]', 'B,1[2/4]', 'B,1[3/4]', 'B,1[4/4]'], ['C,2[1/4]', 'C,2[2/4]', 'C,2[3/4]', 'C,2[4/4]'], ['D,3[1/4]', 'D,3[2/4]', 'D,3[3/4]', 'D,3[4/4]'], ['E,4[1/4]', 'E,4[2/4]', 'E,4[3/4]', 'E,4[4/4]'], ['F,5[1/4]', 'F,5[2/4]', 'F,5[3/4]', 'F,5[4/4]'], ['G,6[1/4]', 'G,6[2/4]', 'G,6[3/4]', 'G,6[4/4]'], ['H,7[1/4]', 'H,7[2/4]', 'H,7[3/4]', 'H,7[4/4]'], ['I,8[1/4]', 'I,8[2/4]', 'I,8[3/4]', 'I,8[4/4]'], ['J,9[1/4]', 'J,9[2/4]', 'J,9[3/4]', 'J,9[4/4]'], ['K,10[1/4]', 'K,10[2/4]', 'K,10[3/4]', 'K,10[4/4]'], ['L,11[1/4]', 'L,11[2/4]', 'L,11[3/4]', 'L,11[4/4]'], ['M,12[1/4]', 'M,12[2/4]', 'M,12[3/4]', 'M,12[4/4]'], ['N,13[1/4]', 'N,13[2/4]', 'N,13[3/4]', 'N,13[4/4]'], ['O,14[1/4]', 'O,14[2/4]', 'O,14[3/4]', 'O,14[4/4]'], ['P,15[1/4]', 'P,15[2/4]', 'P,15[3/4]', 'P,15[4/4]'], ['Q,16[1/4]', 'Q,16[2/4]', 'Q,16[3/4]', 'Q,16[4/4]'], ['R,17[1/4]', 'R,17[2/4]', 'R,17[3/4]', 'R,17[4/4]'], ['S,18[1/4]', 'S,18[2/4]', 'S,18[3/4]', 'S,18[4/4]'], ['T,19[1/4]', 'T,19[2/4]', 'T,19[3/4]', 'T,19[4/4]'], ['U,20[1/4]', 'U,20[2/4]', 'U,20[3/4]', 'U,20[4/4]'], ['V,21[1/4]', 'V,21[2/4]', 'V,21[3/4]', 'V,21[4/4]'], ['W,22[1/4]', 'W,22[2/4]', 'W,22[3/4]', 'W,22[4/4]'], ['X,23[1/4]', 'X,23[2/4]', 'X,23[3/4]', 'X,23[4/4]'], ['Y,24[1/4]', 'Y,24[2/4]', 'Y,24[3/4]', 'Y,24[4/4]'], ['Z,25[1/4]', 'Z,25[2/4]', 'Z,25[3/4]', 'Z,25[4/4]'], ['F,5[1/4]', 'F,5[2/4]', 'F,5[3/4]', 'F,5[4/4]'], ['L,11[1/4]', 'L,11[2/4]', 'L,11[3/4]', 'L,11[4/4]'], ['A,0[1/4]', 'A,0[2/4]', 'A,0[3/4]', 'A,0[4/4]'], ['G,6[1/4]', 'G,6[2/4]', 'G,6[3/4]', 'G,6[4/4]'], ['U,20[1/4]', 'U,20[2/4]', 'U,20[3/4]', 'U,20[4/4]'], ['S,18[1/4]', 'S,18[2/4]', 'S,18[3/4]', 'S,18[4/4]'], ['E,4[1/4]', 'E,4[2/4]', 'E,4[3/4]', 'E,4[4/4]'], ['F,5[1/4]', 'F,5[2/4]', 'F,5[3/4]', 'F,5[4/4]'], ['O,14[1/4]', 'O,14[2/4]', 'O,14[3/4]', 'O,14[4/4]'], ['U,20[1/4]', 'U,20[2/4]', 'U,20[3/4]', 'U,20[4/4]'], ['R,17[1/4]', 'R,17[2/4]', 'R,17[3/4]', 'R,17[4/4]'], ['T,19[1/4]', 'T,19[2/4]', 'T,19[3/4]', 'T,19[4/4]'], ['H,7[1/4]', 'H,7[2/4]', 'H,7[3/4]', 'H,7[4/4]'], ['N,13[1/4]', 'N,13[2/4]', 'N,13[3/4]', 'N,13[4/4]'], ['O,14[1/4]', 'O,14[2/4]', 'O,14[3/4]', 'O,14[4/4]'], ['T,19[1/4]', 'T,19[2/4]', 'T,19[3/4]', 'T,19[4/4]'], ['E,4[1/4]', 'E,4[2/4]', 'E,4[3/4]', 'E,4[4/4]'], ['P,15[1/4]', 'P,15[2/4]', 'P,15[3/4]', 'P,15[4/4]'], ['E,4[1/4]', 'E,4[2/4]', 'E,4[3/4]', 'E,4[4/4]'], ['R,17[1/4]', 'R,17[2/4]', 'R,17[3/4]', 'R,17[4/4]'], ['M,12[1/4]', 'M,12[2/4]', 'M,12[3/4]', 'M,12[4/4]'], ['E,4[1/4]', 'E,4[2/4]', 'E,4[3/4]', 'E,4[4/4]'], ['A,0[1/4]', 'A,0[2/4]', 'A,0[3/4]', 'A,0[4/4]'], ['S,18[1/4]', 'S,18[2/4]', 'S,18[3/4]', 'S,18[4/4]'], ['U,20[1/4]', 'U,20[2/4]', 'U,20[3/4]', 'U,20[4/4]'], ['R,17[1/4]', 'R,17[2/4]', 'R,17[3/4]', 'R,17[4/4]'], ['E,4[1/4]', 'E,4[2/4]', 'E,4[3/4]', 'E,4[4/4]']]
			% Below notes created using 12 divisions of an octave and [c] as a reference pitch

			% Char #0
			<>^"origA,intrmed0[1/4]" e'''4  <>^"origA,intrmed0[2/4]" e''''  <>^"origA,intrmed0[3/4]" g'  <>^"origA,intrmed0[4/4]" c'  
			
			% Char #1
			<>^"origB,intrmed1[1/4]" b'  <>^"origB,intrmed1[2/4]" e''''  <>^"origB,intrmed1[3/4]" c'''  <>^"origB,intrmed1[4/4]" cs'  
			\break
			
			
			% Char #2
			<>^"origC,intrmed2[1/4]" f'''  <>^"origC,intrmed2[2/4]" f''  <>^"origC,intrmed2[3/4]" a'''  <>^"origC,intrmed2[4/4]" d'  
			
			% Char #3
			<>^"origD,intrmed3[1/4]" e''''  <>^"origD,intrmed3[2/4]" e''  <>^"origD,intrmed3[3/4]" b''  <>^"origD,intrmed3[4/4]" ds'  
			\break
			
			
			% Char #4
			<>^"origE,intrmed4[1/4]" e''''  <>^"origE,intrmed4[2/4]" a'''  <>^"origE,intrmed4[3/4]" f''  <>^"origE,intrmed4[4/4]" e'  
			
			% Char #5
			<>^"origF,intrmed5[1/4]" d'  <>^"origF,intrmed5[2/4]" f''  <>^"origF,intrmed5[3/4]" b'  <>^"origF,intrmed5[4/4]" f'  
			\break
			
			
			% Char #6
			<>^"origG,intrmed6[1/4]" c''  <>^"origG,intrmed6[2/4]" a''''  <>^"origG,intrmed6[3/4]" g''''  <>^"origG,intrmed6[4/4]" fs'  
			
			% Char #7
			<>^"origH,intrmed7[1/4]" f'  <>^"origH,intrmed7[2/4]" f''  <>^"origH,intrmed7[3/4]" a'  <>^"origH,intrmed7[4/4]" g'  
			\break
			
			
			% Char #8
			<>^"origI,intrmed8[1/4]" b'  <>^"origI,intrmed8[2/4]" e'''  <>^"origI,intrmed8[3/4]" g''''  <>^"origI,intrmed8[4/4]" gs'  
			
			% Char #9
			<>^"origJ,intrmed9[1/4]" c'''  <>^"origJ,intrmed9[2/4]" d''''  <>^"origJ,intrmed9[3/4]" f'''  <>^"origJ,intrmed9[4/4]" a'  
			\break
			
			
			% Char #10
			<>^"origK,intrmed10[1/4]" f'''  <>^"origK,intrmed10[2/4]" f'  <>^"origK,intrmed10[3/4]" g''  <>^"origK,intrmed10[4/4]" as'  
			
			% Char #11
			<>^"origL,intrmed11[1/4]" f'''  <>^"origL,intrmed11[2/4]" f'''  <>^"origL,intrmed11[3/4]" a'  <>^"origL,intrmed11[4/4]" b'  
			\break
			
			
			% Char #12
			<>^"origM,intrmed12[1/4]" g'  <>^"origM,intrmed12[2/4]" a''''  <>^"origM,intrmed12[3/4]" g'''  <>^"origM,intrmed12[4/4]" c''  
			
			% Char #13
			<>^"origN,intrmed13[1/4]" e'''  <>^"origN,intrmed13[2/4]" a'''  <>^"origN,intrmed13[3/4]" f'''  <>^"origN,intrmed13[4/4]" cs''  
			\break
			
			
			% Char #14
			<>^"origO,intrmed14[1/4]" a'  <>^"origO,intrmed14[2/4]" g''''  <>^"origO,intrmed14[3/4]" g'  <>^"origO,intrmed14[4/4]" d''  
			
			% Char #15
			<>^"origP,intrmed15[1/4]" a''  <>^"origP,intrmed15[2/4]" e'  <>^"origP,intrmed15[3/4]" b'  <>^"origP,intrmed15[4/4]" ds''  
			\break
			
			
			% Char #16
			<>^"origQ,intrmed16[1/4]" d'  <>^"origQ,intrmed16[2/4]" e''''  <>^"origQ,intrmed16[3/4]" d'''  <>^"origQ,intrmed16[4/4]" e''  
			
			% Char #17
			<>^"origR,intrmed17[1/4]" g''  <>^"origR,intrmed17[2/4]" g'''  <>^"origR,intrmed17[3/4]" e'  <>^"origR,intrmed17[4/4]" f''  
			\break
			
			
			% Char #18
			<>^"origS,intrmed18[1/4]" c''''  <>^"origS,intrmed18[2/4]" c''''  <>^"origS,intrmed18[3/4]" e'  <>^"origS,intrmed18[4/4]" fs''  
			
			% Char #19
			<>^"origT,intrmed19[1/4]" c''''  <>^"origT,intrmed19[2/4]" e''  <>^"origT,intrmed19[3/4]" c'''  <>^"origT,intrmed19[4/4]" g''  
			\break
			
			
			% Char #20
			<>^"origU,intrmed20[1/4]" c''''  <>^"origU,intrmed20[2/4]" e'''  <>^"origU,intrmed20[3/4]" c'''  <>^"origU,intrmed20[4/4]" gs''  
			
			% Char #21
			<>^"origV,intrmed21[1/4]" e'  <>^"origV,intrmed21[2/4]" g'''  <>^"origV,intrmed21[3/4]" g'  <>^"origV,intrmed21[4/4]" a''  
			\break
			
			
			% Char #22
			<>^"origW,intrmed22[1/4]" d'''  <>^"origW,intrmed22[2/4]" a'''  <>^"origW,intrmed22[3/4]" e''  <>^"origW,intrmed22[4/4]" as''  
			
			% Char #23
			<>^"origX,intrmed23[1/4]" b'''  <>^"origX,intrmed23[2/4]" d'  <>^"origX,intrmed23[3/4]" f''  <>^"origX,intrmed23[4/4]" b''  
			\break
			
			
			% Char #24
			<>^"origY,intrmed24[1/4]" f'  <>^"origY,intrmed24[2/4]" g''  <>^"origY,intrmed24[3/4]" a'  <>^"origY,intrmed24[4/4]" c'''  
			
			% Char #25
			<>^"origZ,intrmed25[1/4]" b''  <>^"origZ,intrmed25[2/4]" e'  <>^"origZ,intrmed25[3/4]" e''  <>^"origZ,intrmed25[4/4]" cs'''  
			\break
			
			
			% Char #26
			<>^"origF,intrmed5[1/4]" f'''  <>^"origF,intrmed5[2/4]" g'  <>^"origF,intrmed5[3/4]" f''  <>^"origF,intrmed5[4/4]" f'  
			
			% Char #27
			<>^"origL,intrmed11[1/4]" a''''  <>^"origL,intrmed11[2/4]" e''  <>^"origL,intrmed11[3/4]" b''  <>^"origL,intrmed11[4/4]" b'  
			\break
			
			
			% Char #28
			<>^"origA,intrmed0[1/4]" g'''  <>^"origA,intrmed0[2/4]" f''  <>^"origA,intrmed0[3/4]" d''''  <>^"origA,intrmed0[4/4]" c'  
			
			% Char #29
			<>^"origG,intrmed6[1/4]" g'  <>^"origG,intrmed6[2/4]" c'''  <>^"origG,intrmed6[3/4]" g'  <>^"origG,intrmed6[4/4]" fs'  
			\break
			
			
			% Char #30
			<>^"origU,intrmed20[1/4]" e''''  <>^"origU,intrmed20[2/4]" b''  <>^"origU,intrmed20[3/4]" c''''  <>^"origU,intrmed20[4/4]" gs''  
			
			% Char #31
			<>^"origS,intrmed18[1/4]" d'''  <>^"origS,intrmed18[2/4]" a''  <>^"origS,intrmed18[3/4]" e''''  <>^"origS,intrmed18[4/4]" fs''  
			\break
			
			
			% Char #32
			<>^"origE,intrmed4[1/4]" f'''  <>^"origE,intrmed4[2/4]" e''  <>^"origE,intrmed4[3/4]" f'  <>^"origE,intrmed4[4/4]" e'  
			
			% Char #33
			<>^"origF,intrmed5[1/4]" b'''  <>^"origF,intrmed5[2/4]" d''''  <>^"origF,intrmed5[3/4]" c''''  <>^"origF,intrmed5[4/4]" f'  
			\break
			
			
			% Char #34
			<>^"origO,intrmed14[1/4]" a'''  <>^"origO,intrmed14[2/4]" d''''  <>^"origO,intrmed14[3/4]" e'  <>^"origO,intrmed14[4/4]" d''  
			
			% Char #35
			<>^"origU,intrmed20[1/4]" d'''  <>^"origU,intrmed20[2/4]" a''''  <>^"origU,intrmed20[3/4]" b''  <>^"origU,intrmed20[4/4]" gs''  
			\break
			
			
			% Char #36
			<>^"origR,intrmed17[1/4]" b'  <>^"origR,intrmed17[2/4]" g'''  <>^"origR,intrmed17[3/4]" c'''  <>^"origR,intrmed17[4/4]" f''  
			
			% Char #37
			<>^"origT,intrmed19[1/4]" d''''  <>^"origT,intrmed19[2/4]" d''''  <>^"origT,intrmed19[3/4]" b'''  <>^"origT,intrmed19[4/4]" g''  
			\break
			
			
			% Char #38
			<>^"origH,intrmed7[1/4]" d''  <>^"origH,intrmed7[2/4]" a'''  <>^"origH,intrmed7[3/4]" b'''  <>^"origH,intrmed7[4/4]" g'  
			
			% Char #39
			<>^"origN,intrmed13[1/4]" g'''  <>^"origN,intrmed13[2/4]" d''  <>^"origN,intrmed13[3/4]" b'  <>^"origN,intrmed13[4/4]" cs''  
			\break
			
			
			% Char #40
			<>^"origO,intrmed14[1/4]" f'''  <>^"origO,intrmed14[2/4]" b'''  <>^"origO,intrmed14[3/4]" b'  <>^"origO,intrmed14[4/4]" d''  
			
			% Char #41
			<>^"origT,intrmed19[1/4]" f''  <>^"origT,intrmed19[2/4]" g'  <>^"origT,intrmed19[3/4]" d''  <>^"origT,intrmed19[4/4]" g''  
			\break
			
			
			% Char #42
			<>^"origE,intrmed4[1/4]" g''  <>^"origE,intrmed4[2/4]" c'  <>^"origE,intrmed4[3/4]" c'  <>^"origE,intrmed4[4/4]" e'  
			
			% Char #43
			<>^"origP,intrmed15[1/4]" b''  <>^"origP,intrmed15[2/4]" b'''  <>^"origP,intrmed15[3/4]" e'  <>^"origP,intrmed15[4/4]" ds''  
			\break
			
			
			% Char #44
			<>^"origE,intrmed4[1/4]" e'  <>^"origE,intrmed4[2/4]" c'''  <>^"origE,intrmed4[3/4]" d'''  <>^"origE,intrmed4[4/4]" e'  
			
			% Char #45
			<>^"origR,intrmed17[1/4]" g'''  <>^"origR,intrmed17[2/4]" d'''  <>^"origR,intrmed17[3/4]" d''  <>^"origR,intrmed17[4/4]" f''  
			\break
			
			
			% Char #46
			<>^"origM,intrmed12[1/4]" b'  <>^"origM,intrmed12[2/4]" g''  <>^"origM,intrmed12[3/4]" a''''  <>^"origM,intrmed12[4/4]" c''  
			
			% Char #47
			<>^"origE,intrmed4[1/4]" d''''  <>^"origE,intrmed4[2/4]" f'''  <>^"origE,intrmed4[3/4]" f'''  <>^"origE,intrmed4[4/4]" e'  
			\break
			
			
			% Char #48
			<>^"origA,intrmed0[1/4]" b'''  <>^"origA,intrmed0[2/4]" f''  <>^"origA,intrmed0[3/4]" f''''  <>^"origA,intrmed0[4/4]" c'  
			
			% Char #49
			<>^"origS,intrmed18[1/4]" a'''  <>^"origS,intrmed18[2/4]" d'  <>^"origS,intrmed18[3/4]" e''  <>^"origS,intrmed18[4/4]" fs''  
			\break
			
			
			% Char #50
			<>^"origU,intrmed20[1/4]" c'  <>^"origU,intrmed20[2/4]" c''''  <>^"origU,intrmed20[3/4]" g'''  <>^"origU,intrmed20[4/4]" gs''  
			
			% Char #51
			<>^"origR,intrmed17[1/4]" g'  <>^"origR,intrmed17[2/4]" e'  <>^"origR,intrmed17[3/4]" g'''  <>^"origR,intrmed17[4/4]" f''  
			\break
			
			
			% Char #52
			<>^"origE,intrmed4[1/4]" c''  <>^"origE,intrmed4[2/4]" g'  <>^"origE,intrmed4[3/4]" d'  <>^"origE,intrmed4[4/4]" e'  
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


