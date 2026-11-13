
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

			% #0
			c'4           
			% #1
			cs'           
			% #2
			d'            
			% #3
			ds'           
			
			% #4
			e'            
			% #5
			f'            
			% #6
			fs'           
			% #7
			g'            
			\break
			
			
			% #8
			gs'           
			% #9
			a'            
			% #10
			as'           
			% #11
			b'            
			
			% #12
			c''           
			% #13
			cs''          
			% #14
			d''           
			% #15
			ds''          
			\break
			
			
			% #16
			e''           
			% #17
			f''           
			% #18
			fs''          
			% #19
			g''           
			
			% #20
			gs''          
			% #21
			a''           
			% #22
			as''          
			% #23
			b''           
			\break
			
			
			% #24
			c'''          
			% #25
			cs'''         
			% #26
			f'            
			% #27
			b'            
			
			% #28
			c'            
			% #29
			fs'           
			% #30
			ds'           
			% #31
			gs'           
			\break
			
			
			% #32
			fs''          
			% #33
			g''           
			% #34
			c'            
			% #35
			cs''          
			
			% #36
			d'            
			% #37
			e'            
			% #38
			f'            
			% #39
			f''           
			\break
			
			
			% #40
			d''           
			% #41
			c''           
			% #42
			c''           
			% #43
			gs'           
			
			% #44
			ds'           
			% #45
			ds'           
			% #46
			b'            
			% #47
			e'            
			\break
			
			
			% #48
			d'            
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


