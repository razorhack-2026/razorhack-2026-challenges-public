
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

			% #0
			c'4           e'            b'            a'            
			g'            f'            e'            c'            
			\break
			
			
			% #1
			c'            ef'           bf'           a'            
			g'            fs'           ef'           c'            
			\break
			
			
			% #2
			c'            ef'           bf'           a'            
			gf'           fs'           e'            c'            
			\break
			
			
			% #3
			c'            ef'           bf'           a'            
			g'            f'            e'            cs'           
			\break
			
			
			% #4
			c'            ef'           bf'           a'            
			g'            fs'           ef'           cs'           
			\break
			
			
			% #5
			c'            ef'           bf'           af'           
			gf'           f'            ef'           cs'           
			\break
			
			
			% #6
			c'            ef'           bf'           a'            
			g'            f'            ef'           c'            
			\break
			
			
			% #7
			c'            e'            bf'           af'           
			g'            f'            e'            cs'           
			\break
			
			
			% #8
			c'            ef'           bf'           af'           
			g'            fs'           e'            c'            
			\break
			
			
			% #9
			c'            ef'           bf'           af'           
			g'            fs'           ef'           cs'           
			\break
			
			
			% #10
			c'            e'            bf'           af'           
			g'            f'            e'            cs'           
			\break
			
			
			% #11
			c'            e'            bf'           af'           
			g'            fs'           e'            cs'           
			\break
			
			
			% #12
			c'            e'            bf'           af'           
			g'            f'            ef'           cs'           
			\break
			
			
			% #13
			c'            ef'           b'            af'           
			gf'           fs'           ef'           cs'           
			\break
			
			
			% #14
			c'            ef'           bf'           a'            
			gf'           fs'           e'            cs'           
			\break
			
			
			% #15
			c'            e'            bf'           af'           
			g'            f'            e'            c'            
			\break
			
			
			% #16
			c'            ef'           bf'           a'            
			g'            fs'           e'            c'            
			\break
			
			
			% #17
			c'            e'            bf'           af'           
			g'            f'            e'            cs'           
			\break
			
			
			% #18
			c'            ef'           bf'           a'            
			g'            fs'           ef'           c'            
			\break
			
			
			% #19
			c'            e'            bf'           af'           
			g'            f'            e'            cs'           
			\break
			
			
			% #20
			c'            ef'           bf'           a'            
			g'            f'            ef'           cs'           
			\break
			
			
			% #21
			c'            e'            bf'           af'           
			g'            fs'           e'            c'            
			\break
			
			
			% #22
			c'            ef'           bf'           af'           
			g'            fs'           e'            c'            
			\break
			
			
			% #23
			c'            e'            bf'           af'           
			g'            f'            e'            cs'           
			\break
			
			
			% #24
			c'            e'            bf'           af'           
			g'            f'            e'            c'            
			\break
			
			
			% #25
			c'            ef'           bf'           a'            
			gf'           fs'           ef'           c'            
			\break
			
			
			% #26
			c'            e'            bf'           af'           
			g'            fs'           e'            cs'           
			\break
			
			
			% #27
			c'            ef'           b'            af'           
			gf'           fs'           ef'           cs'           
			\break
			
			
			% #28
			c'            ef'           bf'           a'            
			g'            fs'           ef'           c'            
			\break
			
			
			% #29
			c'            e'            bf'           af'           
			g'            fs'           e'            c'            
			\break
			
			
			% #30
			c'            e'            bf'           af'           
			g'            f'            e'            c'            
			\break
			
			
			% #31
			c'            ef'           bf'           a'            
			gf'           fs'           e'            cs'           
			\break
			
			
			% #32
			c'            ef'           b'            af'           
			gf'           fs'           ef'           cs'           
			\break
			
			
			% #33
			c'            ef'           bf'           af'           
			g'            fs'           e'            c'            
			\break
			
			
			% #34
			c'            ef'           bf'           a'            
			gf'           f'            e'            c'            
			\break
			
			
			% #35
			c'            e'            bf'           af'           
			g'            f'            ef'           cs'           
			\break
			
			
			% #36
			c'            ef'           b'            af'           
			gf'           fs'           ef'           cs'           
			\break
			
			
			% #37
			c'            ef'           bf'           af'           
			g'            f'            e'            c'            
			\break
			
			
			% #38
			c'            ef'           bf'           a'            
			gf'           f'            e'            c'            
			\break
			
			
			% #39
			c'            ef'           bf'           af'           
			g'            f'            ef'           c'            
			\break
			
			
			% #40
			c'            e'            bf'           af'           
			g'            fs'           e'            c'            
			\break
			
			
			% #41
			c'            e'            bf'           af'           
			g'            fs'           e'            cs'           
			\break
			
			
			% #42
			c'            e'            bf'           af'           
			g'            f'            ef'           cs'           
			\break
			
			
			% #43
			c'            ef'           bf'           af'           
			gf'           fs'           e'            cs'           
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


