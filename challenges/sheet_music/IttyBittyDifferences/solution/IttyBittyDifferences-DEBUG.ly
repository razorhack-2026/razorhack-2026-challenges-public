
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
	title     = "Itty Bitty Differences"
	subtitle  = "'flag{...}'  keyword is included here."

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
		\tempo 4=200	% Quarter(4) note = 200bpm

		% Actual music notes go below, followed by a closing '}'
		\absolute{
			% !!!!!!!!!!!!!!!!!!!!
			% !!!  DEBUG MODE  !!!
			% !!!!!!!!!!!!!!!!!!!!
			\sectionLabel "Section12"
			% Original text: flag{b1tw153_m0d1f1c4t10n5_f40m_th3_phr453}
			% Intermediate text: [['REFERENCE', 'REFERENCE', 'REFERENCE', 'REFERENCE', 'REFERENCE', 'REFERENCE', 'REFERENCE', 'REFERENCE'], ['f,0', 'f,1', 'f,1', 'f,0', 'f,0', 'f,1', 'f,1', 'f,0'], ['l,0', 'l,1', 'l,1', 'l,0', 'l,1', 'l,1', 'l,0', 'l,0'], ['a,0', 'a,1', 'a,1', 'a,0', 'a,0', 'a,0', 'a,0', 'a,1'], ['g,0', 'g,1', 'g,1', 'g,0', 'g,0', 'g,1', 'g,1', 'g,1'], ['{,0', '{,1', '{,1', '{,1', '{,1', '{,0', '{,1', '{,1'], ['b,0', 'b,1', 'b,1', 'b,0', 'b,0', 'b,0', 'b,1', 'b,0'], ['1,0', '1,0', '1,1', '1,1', '1,0', '1,0', '1,0', '1,1'], ['t,0', 't,1', 't,1', 't,1', 't,0', 't,1', 't,0', 't,0'], ['w,0', 'w,1', 'w,1', 'w,1', 'w,0', 'w,1', 'w,1', 'w,1'], ['1,0', '1,0', '1,1', '1,1', '1,0', '1,0', '1,0', '1,1'], ['5,0', '5,0', '5,1', '5,1', '5,0', '5,1', '5,0', '5,1'], ['3,0', '3,0', '3,1', '3,1', '3,0', '3,0', '3,1', '3,1'], ['_,0', '_,1', '_,0', '_,1', '_,1', '_,1', '_,1', '_,1'], ['m,0', 'm,1', 'm,1', 'm,0', 'm,1', 'm,1', 'm,0', 'm,1'], ['0,0', '0,0', '0,1', '0,1', '0,0', '0,0', '0,0', '0,0'], ['d,0', 'd,1', 'd,1', 'd,0', 'd,0', 'd,1', 'd,0', 'd,0'], ['1,0', '1,0', '1,1', '1,1', '1,0', '1,0', '1,0', '1,1'], ['f,0', 'f,1', 'f,1', 'f,0', 'f,0', 'f,1', 'f,1', 'f,0'], ['1,0', '1,0', '1,1', '1,1', '1,0', '1,0', '1,0', '1,1'], ['c,0', 'c,1', 'c,1', 'c,0', 'c,0', 'c,0', 'c,1', 'c,1'], ['4,0', '4,0', '4,1', '4,1', '4,0', '4,1', '4,0', '4,0'], ['t,0', 't,1', 't,1', 't,1', 't,0', 't,1', 't,0', 't,0'], ['1,0', '1,0', '1,1', '1,1', '1,0', '1,0', '1,0', '1,1'], ['0,0', '0,0', '0,1', '0,1', '0,0', '0,0', '0,0', '0,0'], ['n,0', 'n,1', 'n,1', 'n,0', 'n,1', 'n,1', 'n,1', 'n,0'], ['5,0', '5,0', '5,1', '5,1', '5,0', '5,1', '5,0', '5,1'], ['_,0', '_,1', '_,0', '_,1', '_,1', '_,1', '_,1', '_,1'], ['f,0', 'f,1', 'f,1', 'f,0', 'f,0', 'f,1', 'f,1', 'f,0'], ['4,0', '4,0', '4,1', '4,1', '4,0', '4,1', '4,0', '4,0'], ['0,0', '0,0', '0,1', '0,1', '0,0', '0,0', '0,0', '0,0'], ['m,0', 'm,1', 'm,1', 'm,0', 'm,1', 'm,1', 'm,0', 'm,1'], ['_,0', '_,1', '_,0', '_,1', '_,1', '_,1', '_,1', '_,1'], ['t,0', 't,1', 't,1', 't,1', 't,0', 't,1', 't,0', 't,0'], ['h,0', 'h,1', 'h,1', 'h,0', 'h,1', 'h,0', 'h,0', 'h,0'], ['3,0', '3,0', '3,1', '3,1', '3,0', '3,0', '3,1', '3,1'], ['_,0', '_,1', '_,0', '_,1', '_,1', '_,1', '_,1', '_,1'], ['p,0', 'p,1', 'p,1', 'p,1', 'p,0', 'p,0', 'p,0', 'p,0'], ['h,0', 'h,1', 'h,1', 'h,0', 'h,1', 'h,0', 'h,0', 'h,0'], ['r,0', 'r,1', 'r,1', 'r,1', 'r,0', 'r,0', 'r,1', 'r,0'], ['4,0', '4,0', '4,1', '4,1', '4,0', '4,1', '4,0', '4,0'], ['5,0', '5,0', '5,1', '5,1', '5,0', '5,1', '5,0', '5,1'], ['3,0', '3,0', '3,1', '3,1', '3,0', '3,0', '3,1', '3,1'], ['},0', '},1', '},1', '},1', '},1', '},1', '},0', '},1']]
			% Below notes created using 12 divisions of an octave and [c] as a reference pitch

			% Char #0
			<>^"REFERENCE" c'4    <>^"REFERENCE" e'     <>^"REFERENCE" b'     <>^"REFERENCE" a'     
			<>^"REFERENCE" g'     <>^"REFERENCE" f'     <>^"REFERENCE" e'     <>^"REFERENCE" c'     
			\break
			
			
			% Char #1
			<>^"origf,intrmed0" c'  <>^"origf,intrmed1" ef'  <>^"origf,intrmed1" bf'  <>^"origf,intrmed0" a'  
			<>^"origf,intrmed0" g'  <>^"origf,intrmed1" fs'  <>^"origf,intrmed1" ef'  <>^"origf,intrmed0" c'  
			\break
			
			
			% Char #2
			<>^"origl,intrmed0" c'  <>^"origl,intrmed1" ef'  <>^"origl,intrmed1" bf'  <>^"origl,intrmed0" a'  
			<>^"origl,intrmed1" gf'  <>^"origl,intrmed1" fs'  <>^"origl,intrmed0" e'  <>^"origl,intrmed0" c'  
			\break
			
			
			% Char #3
			<>^"origa,intrmed0" c'  <>^"origa,intrmed1" ef'  <>^"origa,intrmed1" bf'  <>^"origa,intrmed0" a'  
			<>^"origa,intrmed0" g'  <>^"origa,intrmed0" f'  <>^"origa,intrmed0" e'  <>^"origa,intrmed1" cs'  
			\break
			
			
			% Char #4
			<>^"origg,intrmed0" c'  <>^"origg,intrmed1" ef'  <>^"origg,intrmed1" bf'  <>^"origg,intrmed0" a'  
			<>^"origg,intrmed0" g'  <>^"origg,intrmed1" fs'  <>^"origg,intrmed1" ef'  <>^"origg,intrmed1" cs'  
			\break
			
			
			% Char #5
			<>^"orig{,intrmed0" c'  <>^"orig{,intrmed1" ef'  <>^"orig{,intrmed1" bf'  <>^"orig{,intrmed1" af'  
			<>^"orig{,intrmed1" gf'  <>^"orig{,intrmed0" f'  <>^"orig{,intrmed1" ef'  <>^"orig{,intrmed1" cs'  
			\break
			
			
			% Char #6
			<>^"origb,intrmed0" c'  <>^"origb,intrmed1" ef'  <>^"origb,intrmed1" bf'  <>^"origb,intrmed0" a'  
			<>^"origb,intrmed0" g'  <>^"origb,intrmed0" f'  <>^"origb,intrmed1" ef'  <>^"origb,intrmed0" c'  
			\break
			
			
			% Char #7
			<>^"orig1,intrmed0" c'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" bf'  <>^"orig1,intrmed1" af'  
			<>^"orig1,intrmed0" g'  <>^"orig1,intrmed0" f'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" cs'  
			\break
			
			
			% Char #8
			<>^"origt,intrmed0" c'  <>^"origt,intrmed1" ef'  <>^"origt,intrmed1" bf'  <>^"origt,intrmed1" af'  
			<>^"origt,intrmed0" g'  <>^"origt,intrmed1" fs'  <>^"origt,intrmed0" e'  <>^"origt,intrmed0" c'  
			\break
			
			
			% Char #9
			<>^"origw,intrmed0" c'  <>^"origw,intrmed1" ef'  <>^"origw,intrmed1" bf'  <>^"origw,intrmed1" af'  
			<>^"origw,intrmed0" g'  <>^"origw,intrmed1" fs'  <>^"origw,intrmed1" ef'  <>^"origw,intrmed1" cs'  
			\break
			
			
			% Char #10
			<>^"orig1,intrmed0" c'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" bf'  <>^"orig1,intrmed1" af'  
			<>^"orig1,intrmed0" g'  <>^"orig1,intrmed0" f'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" cs'  
			\break
			
			
			% Char #11
			<>^"orig5,intrmed0" c'  <>^"orig5,intrmed0" e'  <>^"orig5,intrmed1" bf'  <>^"orig5,intrmed1" af'  
			<>^"orig5,intrmed0" g'  <>^"orig5,intrmed1" fs'  <>^"orig5,intrmed0" e'  <>^"orig5,intrmed1" cs'  
			\break
			
			
			% Char #12
			<>^"orig3,intrmed0" c'  <>^"orig3,intrmed0" e'  <>^"orig3,intrmed1" bf'  <>^"orig3,intrmed1" af'  
			<>^"orig3,intrmed0" g'  <>^"orig3,intrmed0" f'  <>^"orig3,intrmed1" ef'  <>^"orig3,intrmed1" cs'  
			\break
			
			
			% Char #13
			<>^"orig_,intrmed0" c'  <>^"orig_,intrmed1" ef'  <>^"orig_,intrmed0" b'  <>^"orig_,intrmed1" af'  
			<>^"orig_,intrmed1" gf'  <>^"orig_,intrmed1" fs'  <>^"orig_,intrmed1" ef'  <>^"orig_,intrmed1" cs'  
			\break
			
			
			% Char #14
			<>^"origm,intrmed0" c'  <>^"origm,intrmed1" ef'  <>^"origm,intrmed1" bf'  <>^"origm,intrmed0" a'  
			<>^"origm,intrmed1" gf'  <>^"origm,intrmed1" fs'  <>^"origm,intrmed0" e'  <>^"origm,intrmed1" cs'  
			\break
			
			
			% Char #15
			<>^"orig0,intrmed0" c'  <>^"orig0,intrmed0" e'  <>^"orig0,intrmed1" bf'  <>^"orig0,intrmed1" af'  
			<>^"orig0,intrmed0" g'  <>^"orig0,intrmed0" f'  <>^"orig0,intrmed0" e'  <>^"orig0,intrmed0" c'  
			\break
			
			
			% Char #16
			<>^"origd,intrmed0" c'  <>^"origd,intrmed1" ef'  <>^"origd,intrmed1" bf'  <>^"origd,intrmed0" a'  
			<>^"origd,intrmed0" g'  <>^"origd,intrmed1" fs'  <>^"origd,intrmed0" e'  <>^"origd,intrmed0" c'  
			\break
			
			
			% Char #17
			<>^"orig1,intrmed0" c'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" bf'  <>^"orig1,intrmed1" af'  
			<>^"orig1,intrmed0" g'  <>^"orig1,intrmed0" f'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" cs'  
			\break
			
			
			% Char #18
			<>^"origf,intrmed0" c'  <>^"origf,intrmed1" ef'  <>^"origf,intrmed1" bf'  <>^"origf,intrmed0" a'  
			<>^"origf,intrmed0" g'  <>^"origf,intrmed1" fs'  <>^"origf,intrmed1" ef'  <>^"origf,intrmed0" c'  
			\break
			
			
			% Char #19
			<>^"orig1,intrmed0" c'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" bf'  <>^"orig1,intrmed1" af'  
			<>^"orig1,intrmed0" g'  <>^"orig1,intrmed0" f'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" cs'  
			\break
			
			
			% Char #20
			<>^"origc,intrmed0" c'  <>^"origc,intrmed1" ef'  <>^"origc,intrmed1" bf'  <>^"origc,intrmed0" a'  
			<>^"origc,intrmed0" g'  <>^"origc,intrmed0" f'  <>^"origc,intrmed1" ef'  <>^"origc,intrmed1" cs'  
			\break
			
			
			% Char #21
			<>^"orig4,intrmed0" c'  <>^"orig4,intrmed0" e'  <>^"orig4,intrmed1" bf'  <>^"orig4,intrmed1" af'  
			<>^"orig4,intrmed0" g'  <>^"orig4,intrmed1" fs'  <>^"orig4,intrmed0" e'  <>^"orig4,intrmed0" c'  
			\break
			
			
			% Char #22
			<>^"origt,intrmed0" c'  <>^"origt,intrmed1" ef'  <>^"origt,intrmed1" bf'  <>^"origt,intrmed1" af'  
			<>^"origt,intrmed0" g'  <>^"origt,intrmed1" fs'  <>^"origt,intrmed0" e'  <>^"origt,intrmed0" c'  
			\break
			
			
			% Char #23
			<>^"orig1,intrmed0" c'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" bf'  <>^"orig1,intrmed1" af'  
			<>^"orig1,intrmed0" g'  <>^"orig1,intrmed0" f'  <>^"orig1,intrmed0" e'  <>^"orig1,intrmed1" cs'  
			\break
			
			
			% Char #24
			<>^"orig0,intrmed0" c'  <>^"orig0,intrmed0" e'  <>^"orig0,intrmed1" bf'  <>^"orig0,intrmed1" af'  
			<>^"orig0,intrmed0" g'  <>^"orig0,intrmed0" f'  <>^"orig0,intrmed0" e'  <>^"orig0,intrmed0" c'  
			\break
			
			
			% Char #25
			<>^"orign,intrmed0" c'  <>^"orign,intrmed1" ef'  <>^"orign,intrmed1" bf'  <>^"orign,intrmed0" a'  
			<>^"orign,intrmed1" gf'  <>^"orign,intrmed1" fs'  <>^"orign,intrmed1" ef'  <>^"orign,intrmed0" c'  
			\break
			
			
			% Char #26
			<>^"orig5,intrmed0" c'  <>^"orig5,intrmed0" e'  <>^"orig5,intrmed1" bf'  <>^"orig5,intrmed1" af'  
			<>^"orig5,intrmed0" g'  <>^"orig5,intrmed1" fs'  <>^"orig5,intrmed0" e'  <>^"orig5,intrmed1" cs'  
			\break
			
			
			% Char #27
			<>^"orig_,intrmed0" c'  <>^"orig_,intrmed1" ef'  <>^"orig_,intrmed0" b'  <>^"orig_,intrmed1" af'  
			<>^"orig_,intrmed1" gf'  <>^"orig_,intrmed1" fs'  <>^"orig_,intrmed1" ef'  <>^"orig_,intrmed1" cs'  
			\break
			
			
			% Char #28
			<>^"origf,intrmed0" c'  <>^"origf,intrmed1" ef'  <>^"origf,intrmed1" bf'  <>^"origf,intrmed0" a'  
			<>^"origf,intrmed0" g'  <>^"origf,intrmed1" fs'  <>^"origf,intrmed1" ef'  <>^"origf,intrmed0" c'  
			\break
			
			
			% Char #29
			<>^"orig4,intrmed0" c'  <>^"orig4,intrmed0" e'  <>^"orig4,intrmed1" bf'  <>^"orig4,intrmed1" af'  
			<>^"orig4,intrmed0" g'  <>^"orig4,intrmed1" fs'  <>^"orig4,intrmed0" e'  <>^"orig4,intrmed0" c'  
			\break
			
			
			% Char #30
			<>^"orig0,intrmed0" c'  <>^"orig0,intrmed0" e'  <>^"orig0,intrmed1" bf'  <>^"orig0,intrmed1" af'  
			<>^"orig0,intrmed0" g'  <>^"orig0,intrmed0" f'  <>^"orig0,intrmed0" e'  <>^"orig0,intrmed0" c'  
			\break
			
			
			% Char #31
			<>^"origm,intrmed0" c'  <>^"origm,intrmed1" ef'  <>^"origm,intrmed1" bf'  <>^"origm,intrmed0" a'  
			<>^"origm,intrmed1" gf'  <>^"origm,intrmed1" fs'  <>^"origm,intrmed0" e'  <>^"origm,intrmed1" cs'  
			\break
			
			
			% Char #32
			<>^"orig_,intrmed0" c'  <>^"orig_,intrmed1" ef'  <>^"orig_,intrmed0" b'  <>^"orig_,intrmed1" af'  
			<>^"orig_,intrmed1" gf'  <>^"orig_,intrmed1" fs'  <>^"orig_,intrmed1" ef'  <>^"orig_,intrmed1" cs'  
			\break
			
			
			% Char #33
			<>^"origt,intrmed0" c'  <>^"origt,intrmed1" ef'  <>^"origt,intrmed1" bf'  <>^"origt,intrmed1" af'  
			<>^"origt,intrmed0" g'  <>^"origt,intrmed1" fs'  <>^"origt,intrmed0" e'  <>^"origt,intrmed0" c'  
			\break
			
			
			% Char #34
			<>^"origh,intrmed0" c'  <>^"origh,intrmed1" ef'  <>^"origh,intrmed1" bf'  <>^"origh,intrmed0" a'  
			<>^"origh,intrmed1" gf'  <>^"origh,intrmed0" f'  <>^"origh,intrmed0" e'  <>^"origh,intrmed0" c'  
			\break
			
			
			% Char #35
			<>^"orig3,intrmed0" c'  <>^"orig3,intrmed0" e'  <>^"orig3,intrmed1" bf'  <>^"orig3,intrmed1" af'  
			<>^"orig3,intrmed0" g'  <>^"orig3,intrmed0" f'  <>^"orig3,intrmed1" ef'  <>^"orig3,intrmed1" cs'  
			\break
			
			
			% Char #36
			<>^"orig_,intrmed0" c'  <>^"orig_,intrmed1" ef'  <>^"orig_,intrmed0" b'  <>^"orig_,intrmed1" af'  
			<>^"orig_,intrmed1" gf'  <>^"orig_,intrmed1" fs'  <>^"orig_,intrmed1" ef'  <>^"orig_,intrmed1" cs'  
			\break
			
			
			% Char #37
			<>^"origp,intrmed0" c'  <>^"origp,intrmed1" ef'  <>^"origp,intrmed1" bf'  <>^"origp,intrmed1" af'  
			<>^"origp,intrmed0" g'  <>^"origp,intrmed0" f'  <>^"origp,intrmed0" e'  <>^"origp,intrmed0" c'  
			\break
			
			
			% Char #38
			<>^"origh,intrmed0" c'  <>^"origh,intrmed1" ef'  <>^"origh,intrmed1" bf'  <>^"origh,intrmed0" a'  
			<>^"origh,intrmed1" gf'  <>^"origh,intrmed0" f'  <>^"origh,intrmed0" e'  <>^"origh,intrmed0" c'  
			\break
			
			
			% Char #39
			<>^"origr,intrmed0" c'  <>^"origr,intrmed1" ef'  <>^"origr,intrmed1" bf'  <>^"origr,intrmed1" af'  
			<>^"origr,intrmed0" g'  <>^"origr,intrmed0" f'  <>^"origr,intrmed1" ef'  <>^"origr,intrmed0" c'  
			\break
			
			
			% Char #40
			<>^"orig4,intrmed0" c'  <>^"orig4,intrmed0" e'  <>^"orig4,intrmed1" bf'  <>^"orig4,intrmed1" af'  
			<>^"orig4,intrmed0" g'  <>^"orig4,intrmed1" fs'  <>^"orig4,intrmed0" e'  <>^"orig4,intrmed0" c'  
			\break
			
			
			% Char #41
			<>^"orig5,intrmed0" c'  <>^"orig5,intrmed0" e'  <>^"orig5,intrmed1" bf'  <>^"orig5,intrmed1" af'  
			<>^"orig5,intrmed0" g'  <>^"orig5,intrmed1" fs'  <>^"orig5,intrmed0" e'  <>^"orig5,intrmed1" cs'  
			\break
			
			
			% Char #42
			<>^"orig3,intrmed0" c'  <>^"orig3,intrmed0" e'  <>^"orig3,intrmed1" bf'  <>^"orig3,intrmed1" af'  
			<>^"orig3,intrmed0" g'  <>^"orig3,intrmed0" f'  <>^"orig3,intrmed1" ef'  <>^"orig3,intrmed1" cs'  
			\break
			
			
			% Char #43
			<>^"orig},intrmed0" c'  <>^"orig},intrmed1" ef'  <>^"orig},intrmed1" bf'  <>^"orig},intrmed1" af'  
			<>^"orig},intrmed1" gf'  <>^"orig},intrmed1" fs'  <>^"orig},intrmed0" e'  <>^"orig},intrmed1" cs'  
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


