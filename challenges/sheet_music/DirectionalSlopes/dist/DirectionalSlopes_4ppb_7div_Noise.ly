
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
	title     = "Directional Slopes"
	subtitle  = "'flag{', '}'  keywords are included here."

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
		\tempo 4=300	% Quarter(4) note = 300bpm

		% Actual music notes go below, followed by a closing '}'
		\absolute{

			% #0
			b'4           g'            f'            e'            
			c''           g'            g'            e'            
			c''           c''           f'            d'            
			b'            b'            f'            f'            
			b'            b'            g'            d'            
			c''           b'            f'            d'            
			c''           b'            a'            c'            
			b'            a'            f'            d'            
			\break
			
			
			% #1
			d'            a'            a'            c''           
			e'            f'            a'            c''           
			f'            a'            b'            c''           
			e'            b'            b'            c''           
			e'            b'            b'            b'            
			e'            g'            b'            b'            
			e'            b'            c''           c''           
			f'            f'            b'            c''           
			\break
			
			
			% #2
			c''           c''           a'            f'            
			e'            b'            b'            c''           
			f'            a'            b'            c''           
			c''           a'            g'            c'            
			c''           b'            a'            d'            
			d'            g'            a'            c''           
			e'            g'            b'            c''           
			c''           b'            a'            d'            
			\break
			
			
			% #3
			c''           c''           g'            f'            
			c'            f'            a'            c''           
			d'            a'            b'            c''           
			c''           b'            a'            e'            
			c'            f'            a'            c''           
			c'            a'            a'            c''           
			b'            b'            f'            e'            
			c''           b'            f'            e'            
			\break
			
			
			% #4
			c''           a'            g'            c'            
			f'            g'            g'            c''           
			c'            f'            a'            c''           
			b'            a'            g'            c'            
			c''           b'            b'            c'            
			c''           a'            g'            c'            
			c''           c''           b'            c'            
			d'            g'            c''           c''           
			\break
			
			
			% #5
			b'            b'            a'            c'            
			e'            f'            a'            c''           
			f'            b'            c''           c''           
			c''           b'            a'            d'            
			c''           c''           a'            e'            
			e'            f'            a'            b'            
			c'            g'            c''           c''           
			e'            g'            a'            c''           
			\break
			
			
			% #6
			c''           g'            f'            f'            
			d'            f'            a'            b'            
			e'            a'            b'            c''           
			d'            f'            b'            b'            
			c'            a'            b'            c''           
			c''           b'            f'            f'            
			e'            a'            c''           c''           
			e'            g'            g'            c''           
			\break
			
			
			% #7
			b'            b'            b'            c'            
			d'            g'            c''           c''           
			e'            a'            c''           c''           
			c'            a'            c''           c''           
			c''           b'            a'            d'            
			c''           c''           a'            e'            
			d'            a'            b'            c''           
			f'            g'            a'            c''           
			\break
			
			
			% #8
			b'            g'            g'            e'            
			e'            a'            b'            c''           
			c'            g'            b'            b'            
			b'            a'            a'            e'            
			d'            g'            a'            c''           
			e'            f'            g'            c''           
			b'            a'            g'            c'            
			b'            b'            g'            c'            
			\break
			
			
			% #9
			c''           c''           b'            f'            
			b'            g'            g'            d'            
			c'            f'            c''           c''           
			e'            g'            a'            b'            
			c''           b'            g'            e'            
			c''           b'            b'            c'            
			c''           c''           a'            c'            
			c''           a'            g'            f'            
			\break
			
			
			% #10
			c''           b'            g'            e'            
			d'            a'            a'            b'            
			f'            a'            b'            c''           
			d'            f'            a'            c''           
			c''           b'            a'            e'            
			c''           b'            b'            e'            
			c''           c''           b'            d'            
			c''           b'            g'            f'            
			\break
			
			
			% #11
			c''           b'            a'            d'            
			c''           b'            a'            e'            
			c'            b'            c''           c''           
			e'            f'            a'            c''           
			c''           b'            g'            e'            
			c''           c''           f'            c'            
			c'            a'            b'            b'            
			c'            g'            g'            b'            
			\break
			
			
			% #12
			c''           c''           g'            e'            
			c'            a'            b'            c''           
			c'            f'            g'            c''           
			c'            g'            c''           c''           
			c''           b'            g'            e'            
			c''           b'            f'            f'            
			c'            b'            c''           c''           
			d'            f'            b'            c''           
			\break
			
			
			% #13
			c''           g'            f'            d'            
			d'            g'            a'            b'            
			c''           b'            g'            d'            
			e'            f'            b'            c''           
			f'            f'            b'            c''           
			f'            f'            b'            c''           
			f'            f'            g'            c''           
			f'            g'            a'            c''           
			\break
			
			
			% #14
			c''           a'            a'            c'            
			f'            a'            a'            c''           
			c''           c''           g'            e'            
			c''           c''           a'            f'            
			c'            a'            b'            c''           
			e'            a'            b'            c''           
			d'            f'            g'            b'            
			c''           b'            a'            c'            
			\break
			
			
			% #15
			b'            b'            g'            d'            
			f'            g'            a'            b'            
			c''           b'            g'            d'            
			d'            g'            c''           c''           
			d'            g'            c''           c''           
			d'            g'            g'            c''           
			f'            b'            b'            c''           
			d'            f'            g'            b'            
			\break
			
			
			% #16
			c''           c''           g'            f'            
			e'            f'            b'            c''           
			c''           b'            g'            d'            
			c''           b'            a'            c'            
			c''           c''           g'            d'            
			d'            g'            a'            c''           
			c''           b'            g'            e'            
			c''           a'            g'            e'            
			\break
			
			
			% #17
			c''           g'            g'            e'            
			c''           c''           b'            c'            
			d'            g'            g'            c''           
			e'            g'            b'            c''           
			b'            b'            a'            e'            
			c''           a'            a'            f'            
			d'            f'            b'            c''           
			f'            a'            c''           c''           
			\break
			
			
			% #18
			c''           b'            b'            c'            
			f'            g'            b'            c''           
			e'            a'            b'            c''           
			f'            g'            b'            c''           
			c''           b'            b'            e'            
			b'            a'            g'            e'            
			d'            a'            b'            c''           
			c''           c''           b'            f'            
			\break
			
			
			% #19
			c''           b'            g'            c'            
			c''           b'            g'            c'            
			c'            g'            c''           c''           
			e'            f'            a'            c''           
			c''           b'            b'            d'            
			c''           b'            a'            f'            
			c''           b'            a'            f'            
			f'            b'            c''           c''           
			\break
			
			
			% #20
			c''           b'            b'            c'            
			c'            b'            c''           c''           
			d'            f'            c''           c''           
			f'            a'            a'            c''           
			c''           c''           b'            c'            
			c'            f'            a'            c''           
			c'            a'            b'            c''           
			c''           b'            g'            d'            
			\break
			
			
			% #21
			c''           b'            g'            f'            
			c''           c''           f'            f'            
			d'            f'            c''           c''           
			f'            f'            c''           c''           
			c''           g'            g'            d'            
			f'            g'            b'            b'            
			c''           c''           b'            c'            
			c''           c''           f'            d'            
			\break
			
			
			% #22
			b'            g'            f'            d'            
			e'            a'            b'            c''           
			e'            g'            b'            b'            
			f'            a'            a'            b'            
			c''           b'            g'            c'            
			e'            a'            a'            b'            
			c''           a'            g'            f'            
			c''           b'            a'            d'            
			\break
			
			
			% #23
			c''           b'            g'            c'            
			c''           a'            f'            f'            
			d'            a'            c''           c''           
			c'            g'            a'            c''           
			c''           a'            g'            d'            
			c''           c''           f'            d'            
			c''           c''           a'            e'            
			c'            g'            b'            b'            
			\break
			
			
			% #24
			c''           g'            f'            f'            
			f'            g'            a'            b'            
			f'            b'            c''           c''           
			e'            g'            c''           c''           
			b'            a'            f'            f'            
			f'            a'            a'            c''           
			c'            b'            c''           c''           
			b'            a'            g'            f'            
			\break
			
			
			% #25
			c''           c''           b'            d'            
			c''           a'            a'            c'            
			f'            g'            b'            c''           
			c'            a'            c''           c''           
			c''           a'            f'            e'            
			c''           a'            f'            f'            
			e'            g'            a'            b'            
			c'            a'            c''           c''           
			\break
			
			
			% #26
			b'            a'            g'            d'            
			d'            f'            g'            c''           
			e'            g'            g'            c''           
			f'            f'            g'            c''           
			b'            a'            g'            d'            
			c''           g'            g'            e'            
			c'            f'            b'            c''           
			c'            a'            a'            c''           
			\break
			
			
			% #27
			c''           b'            b'            c'            
			d'            b'            b'            c''           
			c''           c''           b'            e'            
			c'            f'            b'            c''           
			d'            f'            a'            c''           
			f'            b'            c''           c''           
			d'            b'            b'            b'            
			e'            g'            b'            c''           
			\break
			
			
			% #28
			c''           b'            g'            d'            
			c'            f'            g'            b'            
			c''           b'            b'            d'            
			f'            g'            c''           c''           
			c''           b'            a'            c'            
			c''           c''           f'            c'            
			e'            b'            c''           c''           
			c''           b'            a'            c'            
			\break
			
			
			% #29
			c''           c''           g'            f'            
			c'            a'            c''           c''           
			c''           b'            b'            e'            
			c'            a'            a'            b'            
			d'            f'            b'            c''           
			c'            a'            a'            b'            
			e'            g'            b'            c''           
			e'            g'            a'            c''           
			\break
			
			
			% #30
			c''           a'            g'            f'            
			e'            b'            c''           c''           
			c''           c''           b'            f'            
			c''           a'            g'            f'            
			b'            g'            f'            d'            
			e'            a'            b'            c''           
			e'            g'            b'            b'            
			d'            g'            b'            c''           
			\break
			
			
			% #31
			c''           b'            a'            d'            
			f'            g'            c''           c''           
			f'            f'            c''           c''           
			c'            b'            c''           c''           
			c''           g'            f'            f'            
			c''           g'            g'            c'            
			e'            g'            b'            c''           
			c''           g'            f'            c'            
			\break
			
			
			% #32
			c''           c''           b'            c'            
			c''           a'            g'            f'            
			f'            g'            g'            c''           
			e'            b'            b'            b'            
			c''           a'            f'            c'            
			c'            g'            g'            b'            
			c''           b'            a'            e'            
			b'            a'            f'            f'            
			\break
			
			
			% #33
			c''           c''           b'            d'            
			e'            g'            g'            c''           
			b'            a'            f'            d'            
			e'            f'            g'            c''           
			c''           g'            f'            e'            
			c'            g'            a'            c''           
			c''           c''           a'            e'            
			b'            b'            a'            e'            
			\break
			
			
			% #34
			c''           b'            a'            d'            
			c''           a'            g'            c'            
			f'            g'            c''           c''           
			c'            g'            b'            b'            
			c''           g'            f'            e'            
			c''           b'            f'            f'            
			f'            f'            a'            c''           
			f'            a'            b'            b'            
			\break
			
			
			% #35
			c''           c''           b'            d'            
			c''           a'            g'            c'            
			e'            g'            c''           c''           
			c''           b'            a'            e'            
			c''           g'            f'            f'            
			c''           c''           b'            f'            
			c''           c''           f'            f'            
			f'            b'            c''           c''           
			\break
			
			
			% #36
			c''           b'            a'            f'            
			c'            f'            c''           c''           
			e'            g'            a'            c''           
			c'            a'            c''           c''           
			f'            g'            g'            b'            
			f'            b'            c''           c''           
			c''           c''           a'            c'            
			c'            a'            c''           c''           
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


