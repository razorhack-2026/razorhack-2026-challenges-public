
\version "2.26.0"
\language "english"

\header {
	title     = "HCH 2 Tutorial (No Flag): Meecro Micro"
	subtitle    = "Whole step: C/Dbb -> C##/D.  Half steps: C -> C#/Db -> D."
	subsubtitle = "Quarter Steps: C -> Cqs/Dtqf -> Cs/Db -> Ctqs/Dqf -> D"
	composer  = "Mort"
	copyright = "Copyright is CopyLeft"
}



global = {
	\key c \major
	\numericTimeSignature
		\time 4/4
	\tempo 4=120	%Quarter(4) note = 120bpm
}

right = \relative c' {
	\global
	% Music follows here.
	\time 4/4
	c->^"*Half steps" cs d-> ds |
	e-> f2->^"E#==F" fs4 |
	g-> gs a-> as |
	b-> c2->^"B#==C"
	r4 |
	r1 |
	
	a4->^"*Quarter steps" aqs as atqs |
	
	\time 2/4
	b-> bqs |
	
	% bs^"X Equivalent to C"
	%btqs  |
	c->^"V 1/4 step lower than Btqs, B#==C"
	cqs^"V Equivalent to Btqs" |
	
	cs ctqs
	
	\time 4/4
	d-> dqs ds dtqs |
	e1-> |
	e4-> eqf ef etqf |
	d-> dqf df dtqf  |
	c1-> |
	
	r1   |
	e4->^"0b"^"*Enharmonic (equivalent) notes" eqf^"0.5b" ef^"1b" etqf^"1.5b" |
	d->^"bb"
	r2. |
}


left = \relative c' {
	\global
	% Music follows here.
	\time 4/4
	c4 cs d ds |
	e es2 fs4 |
	g gs a as |
	b bs2
	r4 |
	r1 |
	r1 |
	
	b4 bqs bs btqs  |
	%c^"X Lower than btqs"
	%cqs^"X Equivalent to btqs"
	cs ctqs |
	
	r1 |
	r  |
	r  |
	r  |
	r  |
	r  |
	dss4^"##" dtqs^"1.5#" ds^"#" dqs^"0.5#" |
	d^"0#" r2. |
}




\score {
	<<%simultaneously-occurring staves
		\new PianoStaff \with {
			instrumentName = "Piano"
			\override StaffGrouper.staff-staff-spacing =
				#'((basic-distance . 0)
				   (minimum-distance . 0)
				   (padding . 0)
				   (stretchability . 0))
		} <<
			\new Staff = "right" \with {
				midiInstrument = "acoustic grand"
			} \right
			\new Staff = "left" \with {
				midiInstrument = "acoustic grand"
			} { \clef treble \left }
		>>
		\new StaffGroup << >>
	>>
	\layout { }
	\midi { }
}

