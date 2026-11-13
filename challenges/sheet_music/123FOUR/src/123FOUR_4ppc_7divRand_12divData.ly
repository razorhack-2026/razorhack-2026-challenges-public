
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

			% #0
			e'''4         e''''         g'            c'            
			
			% #1
			b'            e''''         c'''          cs'           
			\break
			
			
			% #2
			f'''          f''           a'''          d'            
			
			% #3
			e''''         e''           b''           ds'           
			\break
			
			
			% #4
			e''''         a'''          f''           e'            
			
			% #5
			d'            f''           b'            f'            
			\break
			
			
			% #6
			c''           a''''         g''''         fs'           
			
			% #7
			f'            f''           a'            g'            
			\break
			
			
			% #8
			b'            e'''          g''''         gs'           
			
			% #9
			c'''          d''''         f'''          a'            
			\break
			
			
			% #10
			f'''          f'            g''           as'           
			
			% #11
			f'''          f'''          a'            b'            
			\break
			
			
			% #12
			g'            a''''         g'''          c''           
			
			% #13
			e'''          a'''          f'''          cs''          
			\break
			
			
			% #14
			a'            g''''         g'            d''           
			
			% #15
			a''           e'            b'            ds''          
			\break
			
			
			% #16
			d'            e''''         d'''          e''           
			
			% #17
			g''           g'''          e'            f''           
			\break
			
			
			% #18
			c''''         c''''         e'            fs''          
			
			% #19
			c''''         e''           c'''          g''           
			\break
			
			
			% #20
			c''''         e'''          c'''          gs''          
			
			% #21
			e'            g'''          g'            a''           
			\break
			
			
			% #22
			d'''          a'''          e''           as''          
			
			% #23
			b'''          d'            f''           b''           
			\break
			
			
			% #24
			f'            g''           a'            c'''          
			
			% #25
			b''           e'            e''           cs'''         
			\break
			
			
			% #26
			f'''          g'            f''           f'            
			
			% #27
			a''''         e''           b''           b'            
			\break
			
			
			% #28
			g'''          f''           d''''         c'            
			
			% #29
			g'            c'''          g'            fs'           
			\break
			
			
			% #30
			e''''         b''           c''''         gs''          
			
			% #31
			d'''          a''           e''''         fs''          
			\break
			
			
			% #32
			f'''          e''           f'            e'            
			
			% #33
			b'''          d''''         c''''         f'            
			\break
			
			
			% #34
			a'''          d''''         e'            d''           
			
			% #35
			d'''          a''''         b''           gs''          
			\break
			
			
			% #36
			b'            g'''          c'''          f''           
			
			% #37
			d''''         d''''         b'''          g''           
			\break
			
			
			% #38
			d''           a'''          b'''          g'            
			
			% #39
			g'''          d''           b'            cs''          
			\break
			
			
			% #40
			f'''          b'''          b'            d''           
			
			% #41
			f''           g'            d''           g''           
			\break
			
			
			% #42
			g''           c'            c'            e'            
			
			% #43
			b''           b'''          e'            ds''          
			\break
			
			
			% #44
			e'            c'''          d'''          e'            
			
			% #45
			g'''          d'''          d''           f''           
			\break
			
			
			% #46
			b'            g''           a''''         c''           
			
			% #47
			d''''         f'''          f'''          e'            
			\break
			
			
			% #48
			b'''          f''           f''''         c'            
			
			% #49
			a'''          d'            e''           fs''          
			\break
			
			
			% #50
			c'            c''''         g'''          gs''          
			
			% #51
			g'            e'            g'''          f''           
			\break
			
			
			% #52
			c''           g'            d'            e'            
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


