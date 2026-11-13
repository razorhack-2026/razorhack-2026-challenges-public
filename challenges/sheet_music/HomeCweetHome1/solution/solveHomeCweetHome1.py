import re

def decode_lilypond_flag(filepath):
	"""Extract and decode the embedded flag from a LilyPond file."""

	"""
	| Index | Note | Letter | | Index | Note | Letter |
	|-------|------|--------|-|-------|------|--------|
	| 0     | c'   | A      | | 13    | cs'' | N |
	| 1     | cs'  | B      | | 14    | d''  | O |
	| 2     | d'   | C      | | 15    | ds'' | P |
	| 3     | ds'  | D      | | 16    | e''  | Q |
	| 4     | e'   | E      | | 17    | f''  | R |
	| 5     | f'   | F      | | 18    | fs'' | S |
	| 6     | fs'  | G      | | 19    | g''  | T |
	| 7     | g'   | H      | | 20    | gs'' | U |
	| 8     | gs'  | I      | | 21    | a''  | V |
	| 9     | a'   | J      | | 22    | as'' | W |
	| 10    | as'  | K      | | 23    | b''  | X |
	| 11    | b'   | L      | | 24    | c''' | Y |
	| 12    | c''  | M      | | 25    | cs'''| Z |
	"""
	# Goal: Mapping: pitch_index (int) OR note_name (str) -> English_letter (A-Z)
	# index_to_letter = {
	# 	0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F',
	# 	6: 'G', 7: 'H', 8: 'I', 9: 'J', 10: 'K', 11: 'L',
	# 	12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R',
	# 	18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X',
	# 	24: 'Y', 25: 'Z'
	# }
  
	# Intermediate Mapping 1: Index -> Note Name (apostrophes preserved)
	index_to_note = {
		0: "c'", 1: "cs'", 2: "d'", 3: "ds'", 4: "e'", 5: "f'",
		6: "fs'", 7: "g'", 8: "gs'", 9: "a'", 10: "as'", 11: "b'",
		12: "c''", 13: "cs''", 14: "d''", 15: "ds''", 16: "e''", 17: "f''",
		18: "fs''", 19: "g''", 20: "gs''", 21: "a''", 22: "as''", 23: "b''",
		24: "c'''", 25: "cs'''"
	}
	# Intermediate Mapping 2: Note Name -> English Letter
	note_to_letter = {
		"c'": 'A', "cs'": 'B', "d'": 'C', "ds'": 'D', "e'": 'E', "f'": 'F',
		"fs'": 'G', "g'": 'H', "gs'": 'I', "a'": 'J', "as'": 'K', "b'": 'L',
		"c''": 'M', "cs''": 'N', "d''": 'O', "ds''": 'P', "e''": 'Q', "f''": 'R',
		"fs''": 'S', "g''": 'T', "gs''": 'U', "a''": 'V', "as''": 'W', "b''": 'X',
		"c'''": 'Y', "cs'''": 'Z'
	}

	def get_note_from_index(index: int) -> str:
		"""Returns pitch string with apostrophes intact."""
		return index_to_note.get(index, "[BAD_NOTE]")

	def get_letter_from_note(note: str) -> str:
		"""Returns English letter corresponding to pitch string."""
		return note_to_letter.get(note, "[BAD_LETTER]")

	def index_to_letter_chained(index: int) -> str:
		"""Chained execution: Index -> Note -> Letter."""
		note = get_note_from_index(index)
		return get_letter_from_note(note)
	
	with open(filepath, 'r') as f:
		content = f.read()
	
	# Find all lines with comment indices: % #NUMBER  (e.g., "% #0")
	# followed by a note on the next non-empty line
	pattern = r'%\s*#(\d+)\s*\n\s*(\w+[\'\"]*)'
	matches = re.findall(pattern, content)
	
	# Extract indices >= 26 (the encoded message)
	extracted_message, msg_after_definition = [], []
	for index_str, note in matches:
		# print(get_letter_from_note(note))
		msg_after_definition.append(get_letter_from_note(note))
		index = int(index_str)
		if index >= 26:  # Skip the lookup table definition pitches (0-25)
			extracted_message.append(get_letter_from_note(note))
	
	return ''.join(msg_after_definition), ''.join(extracted_message)

# Usage
LilycodeFilepath = '../dist/HomeCweetHome1.ly'	# MAY NEED TO CHANGE THIS FILEPATH
flag_strs = decode_lilypond_flag(LilycodeFilepath)
print(f"Encoded Message(s):")
[print(f"* {flag}") for flag in flag_strs]
# Expected: FLAGDISTANCEFROMMIDDLEC