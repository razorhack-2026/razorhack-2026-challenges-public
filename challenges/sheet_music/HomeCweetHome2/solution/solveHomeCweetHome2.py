import re

def decode_lilypond_flag(filepath:str, DEBUG:bool):
	# """Extract and decode embedded flag from LilyPond file using English 24-TET Quarter-Tones."""

	# # Messed up enharmonics
	# """
	# | Index | Note  | Letter | | Index | Note  | Letter |
	# |-------|-------|--------|-|-------|-------|--------|
	# | 0     | a     | A      | | 13    | dqs'  | N      |
	# | 1     | aqs   | B      | | 14    | ds'   | O      |
	# | 2     | as    | C      | | 15    | dtqs' | P      |
	# | 3     | atqs  | D      | | 16    | e'    | Q      |
	# | 4     | b     | E      | | 17    | eqs'  | R      |
	# | 5     | bqs   | F      | | 18    | es'   | S      |
	# | 6     | bs    | G      | | 19    | etqs' | T      |
	# | 7     | btqs  | H      | | 20    | f'    | U      |
	# | 8     | c'    | I      | | 21    | fqs'  | V      |
	# | 9     | cqs'  | J      | | 22    | fs'   | W      |
	# | 10    | cs'   | K      | | 23    | ftqs' | X      |
	# | 11    | ctqs' | L      | | 24    | g'    | Y      |
	# | 12    | d'    | M      | | 25    | gqs'  | Z      |
	# """
	# ^^^ AI-generated. Messed up the fact that B# is equivalent to C and E# is equivalent to F. bs, btqs, etqs, es should each not exist.

	"""Extract and decode embedded flag from LilyPond file using English 24-TET Quarter-Tones (Enharmonically Correct)."""
	"""
	| Index | Note  | Letter | | Index | Note  | Letter |
	|-------|-------|--------|-|-------|-------|--------|
	| 0     | a     | A      | | 13    | dtqs' | N      |
	| 1     | aqs   | B      | | 14    | e'    | O      |
	| 2     | as    | C      | | 15    | eqs'  | P      |
	| 3     | atqs  | D      | | 16    | f'    | Q      |
	| 4     | b     | E      | | 17    | fqs'  | R      |
	| 5     | bqs   | F      | | 18    | fs'   | S      |
	| 6     | c'    | G      | | 19    | ftqs' | T      |
	| 7     | cqs'  | H      | | 20    | g'    | U      |
	| 8     | cs'   | I      | | 21    | gqs'  | V      |
	| 9     | ctqs' | J      | | 22    | gs'   | W      |
	| 10    | d'    | K      | | 23    | gtqs' | X      |
	| 11    | dqs'  | L      | | 24    | a'    | Y      |
	| 12    | ds'   | M      | | 25    | aqs'  | Z      |
	"""

	# Goal: Mapping: pitch_index (int) OR note_name (str) -> English_letter (A-Z)
	# index_to_letter = {
	#   0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F',
	#   6: 'G', 7: 'H', 8: 'I', 9: 'J', 10: 'K', 11: 'L',
	#   12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R',
	#   18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X',
	#   24: 'Y', 25: 'Z'
	# }
  

	# Intermediate Mapping 1: Index -> Note Name (apostrophes preserved)
	# 
	# Messed up enharmonics
	# Base note is "a" (no apostrophe). English (not Dutch) quarter-tone increments: natural, quarter-sharp (qs), sharp (s), three-quarter-sharp (tqs).
	# Octave boundary adds apostrophe at "c'" (Index 8).
	# index_to_note = {
	# 	0: "a",     1: "aqs",   2: "as",    3: "atqs",  
	# 	4: "b",     5: "bqs",   6: "bs",    7: "btqs",  
	# 	8: "c'",    9: "cqs'",  10: "cs'",  11: "ctqs'", 
	# 	12: "d'",   13: "dqs'", 14: "ds'",  15: "dtqs'", 
	# 	16: "e'",   17: "eqs'", 18: "es'",  19: "etqs'", 
	# 	20: "f'",   21: "fqs'", 22: "fs'",  23: "ftqs'", 
	# 	24: "g'",   25: "gqs'"
	# }
	# Corrected enharmonics
	# Base note is "a" (no apostrophe). English (not Dutch) quarter-tone increments: natural, quarter-sharp (qs), sharp (s), three-quarter-sharp (tqs).
	# Correct 24-TET scale: B and E have only natural and qs (no bs, btqs, es, etqs). Octave boundary adds apostrophe at "c'" (Index 6).
	index_to_note = {
		0: "a",     1: "aqs",   2: "as",    3: "atqs",  
		4: "b",     5: "bqs",   6: "c'",    7: "cqs'",  
		8: "cs'",   9: "ctqs'", 10: "d'",   11: "dqs'", 
		12: "ds'",  13: "dtqs'", 14: "e'",  15: "eqs'", 
		16: "f'",   17: "fqs'", 18: "fs'",  19: "ftqs'", 
		20: "g'",   21: "gqs'", 22: "gs'",  23: "gtqs'", 
		24: "a'",   25: "aqs'"
	}



	# Intermediate Mapping 2: Note Name -> English Letter
	# 
	# Messed up enharmonics
	# note_to_letter = {
	# 	"a": 'A',     "aqs": 'B',   "as": 'C',    "atqs": 'D',  
	# 	"b": 'E',     "bqs": 'F',   "bs": 'G',    "btqs": 'H',  
	# 	"c'": 'I',    "cqs'": 'J',  "cs'": 'K',   "ctqs'": 'L', 
	# 	"d'": 'M',    "dqs'": 'N',  "ds'": 'O',   "dtqs'": 'P', 
	# 	"e'": 'Q',    "eqs'": 'R',  "es'": 'S',   "etqs'": 'T', 
	# 	"f'": 'U',    "fqs'": 'V',  "fs'": 'W',   "ftqs'": 'X', 
	# 	"g'": 'Y',    "gqs'": 'Z'
	# }
	# Corrected enharmonics
	note_to_letter = {
		"a": 'A',     "aqs": 'B',   "as": 'C',    "atqs": 'D',  
		"b": 'E',     "bqs": 'F',   "c'": 'G',    "cqs'": 'H',  
		"cs'": 'I',   "ctqs'": 'J', "d'": 'K',    "dqs'": 'L', 
		"ds'": 'M',   "dtqs'": 'N', "e'": 'O',    "eqs'": 'P', 
		"f'": 'Q',    "fqs'": 'R',  "fs'": 'S',   "ftqs'": 'T', 
		"g'": 'U',    "gqs'": 'V',  "gs'": 'W',   "gtqs'": 'X', 
		"a'": 'Y',    "aqs'": 'Z'
	}

	def get_note_from_index(index: int) -> str:
		"""Returns pitch string with apostrophes intact."""
		# return index_to_note.get(index, "[BAD_NOTE]")
		return index_to_note.get(index, "`")

	def get_letter_from_note(note: str) -> str:
		"""Returns English letter corresponding to pitch string."""
		return note_to_letter.get(note, "~")

	def index_to_letter_chained(index: int) -> str:
		"""Chained execution: Index -> Note -> Letter."""
		note = get_note_from_index(index)
		return get_letter_from_note(note)
	
	with open(filepath, 'r') as f:
		content = f.read()
	
	# Find all lines with comment indices: % #NUMBER  (e.g., "% #0")
	#   followed by a note on the next non-empty line.
	# pattern = r'%\s*#(\d+)\s*\n\s*(\w+[\'\"]*)'	# Messes up on "a4" because "4" is part of a word (\w)
	# pattern = r'%\s*#(\d+)\s*\n\s*([a-z]+[\'\"]*)'
	pattern = r'%\s*#(\d+)\s*(?:\n)*\s*([a-z]+[\',]*)'
	matches = re.findall(pattern, content)
	if DEBUG: print(matches)
	
	# Extract indices >= 26 (the encoded message)
	extracted_message, msg_after_definition = [], []
	for index_str, note in matches:
		if DEBUG: print(index_str, get_letter_from_note(note))
		msg_after_definition.append(get_letter_from_note(note))
		index = int(index_str)
		if index >= 26:  # Skip the lookup table definition pitches (0-25)
			extracted_message.append(get_letter_from_note(note))
	
	return ''.join(msg_after_definition), ''.join(extracted_message)

# Usage
LilycodeFilepath = '../dist/HomeCweetHome2.ly'  # MAY NEED TO CHANGE THIS FILEPATH
flag_strs = decode_lilypond_flag(LilycodeFilepath, DEBUG=False)
print(f"Encoded Message(s):")
[print(f"* {flag}") for flag in flag_strs]
# Expected Output:
# Encoded Message(s):
# * ABCDEFGHIJKLMNOPQRSTUVWXYZFLAGDISTANCEFROMTHELETTERABELOWMIDDLEC
# * FLAGDISTANCEFROMTHELETTERABELOWMIDDLEC