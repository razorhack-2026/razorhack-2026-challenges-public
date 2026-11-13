
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

			% #0
			a4            
			% #1
			aqs           
			% #2
			as            
			% #3
			atqs          
			
			% #4
			b             
			% #5
			bqs           
			% #6
			c'            
			% #7
			cqs'          
			\break
			
			
			% #8
			cs'           
			% #9
			ctqs'         
			% #10
			d'            
			% #11
			dqs'          
			
			% #12
			ds'           
			% #13
			dtqs'         
			% #14
			e'            
			% #15
			eqs'          
			\break
			
			
			% #16
			f'            
			% #17
			fqs'          
			% #18
			fs'           
			% #19
			ftqs'         
			
			% #20
			g'            
			% #21
			gqs'          
			% #22
			gs'           
			% #23
			gtqs'         
			\break
			
			
			% #24
			a'            
			% #25
			aqs'          
			% #26
			bqs           
			% #27
			dqs'          
			
			% #28
			a             
			% #29
			c'            
			% #30
			atqs          
			% #31
			cs'           
			\break
			
			
			% #32
			fs'           
			% #33
			ftqs'         
			% #34
			a             
			% #35
			dtqs'         
			
			% #36
			as            
			% #37
			b             
			% #38
			bqs           
			% #39
			fqs'          
			\break
			
			
			% #40
			e'            
			% #41
			ds'           
			% #42
			ftqs'         
			% #43
			cqs'          
			
			% #44
			b             
			% #45
			dqs'          
			% #46
			b             
			% #47
			ftqs'         
			\break
			
			
			% #48
			ftqs'         
			% #49
			b             
			% #50
			fqs'          
			% #51
			a             
			
			% #52
			aqs           
			% #53
			b             
			% #54
			dqs'          
			% #55
			e'            
			\break
			
			
			% #56
			gs'           
			% #57
			ds'           
			% #58
			cs'           
			% #59
			atqs          
			
			% #60
			atqs          
			% #61
			dqs'          
			% #62
			b             
			% #63
			as            
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


