
import re

def getLyNotesText(filename:str) -> str:
	with open(filename, "r") as f:
		ly_content = f.read()
	ly_notes_text = re.search(r'\\absolute\s*\{(.*?)\}', ly_content, re.DOTALL).group(1)	# <insert absolute notes from .ly file here>
	return ly_notes_text


ly_text = getLyNotesText("../dist/DirectionalSlopes_4ppb_7div_Noise.ly")


""" Parse all notes. """
# Remove comments and line breaks
lines = ly_text.splitlines()
notes = []
for line in lines:
	line = re.sub(r'%.*', '', line).strip()
	if not line or line.startswith('\\'):
		continue
	# Extract note names
	tokens = line.split()
	for tok in tokens:
		# Note token like b'4 or g'
		m = re.match(r'([a-g][\'\']*)(\d*)', tok)
		if m:
			notes.append(m.group(1))

print(f"Total notes count: {len(notes)}")
print(f"Notes per measure / group (4 per measure?): total measures = {len(notes)/4}")

"""
OUTPUT
Total notes count: 1184
Notes per measure / group (4 per measure?): total measures = 296.0
"""





# All of this block of code assumes that pitches exist within just ONE octave
#   (i.e., assumes that multi-octave spans are not present)

unique_notes = sorted(list(set(notes)))
print("Unique notes:", unique_notes)

# Mapping to pitch degree / pitch value in C major
# Note pitch ordering: c' < d' < e' < f' < g' < a' < b' < c''
note_to_val = {
	"c'": 0,
	"d'": 1,
	"e'": 2,
	"f'": 3,
	"g'": 4,
	"a'": 5,
	"b'": 6,
	"c''": 7
}

val_notes = [note_to_val[n] for n in notes]
print("First 32 note values:", val_notes[:32])
"""
OUTPUT
Unique notes: ["a'", "b'", "c'", "c''", "d'", "e'", "f'", "g'"]
First 32 note values: [6, 4, 3, 2, 7, 4, 4, 2, 7, 7, 3, 1, 6, 6, 3, 3, 6, 6, 4, 1, 7, 6, 3, 1, 7, 6, 5, 0, 6, 5, 3, 1]
"""





""" Get note-by-note pitch differences. """

# Let's inspect the 4-note blocks (3 differences per block? or 4 differences if chained?)
blocks = [val_notes[i:i+4] for i in range(0, len(val_notes), 4)]

print("First 10 blocks (absolute values):")
for i, b in enumerate(blocks[:10]):
	print(f"Block {i}: {b}")

print("\nDifferences within each 4-note block (b[1]-b[0], b[2]-b[1], b[3]-b[2]):")
for i, b in enumerate(blocks[:10]):
	diffs = [b[j+1] - b[j] for j in range(3)]
	print(f"Block {i}: diffs={diffs}")

print("\nDifferences with previous note (chaining across entire song):")
chain_diffs = [val_notes[i+1] - val_notes[i] for i in range(len(val_notes)-1)]
print("First 20 chain diffs:", chain_diffs[:20])
"""
OUTPUT:
First 10 blocks (absolute values):
Block 0: [6, 4, 3, 2]
Block 1: [7, 4, 4, 2]
Block 2: [7, 7, 3, 1]
Block 3: [6, 6, 3, 3]
Block 4: [6, 6, 4, 1]
Block 5: [7, 6, 3, 1]
Block 6: [7, 6, 5, 0]
Block 7: [6, 5, 3, 1]
Block 8: [1, 5, 5, 7]
Block 9: [2, 3, 5, 7]

Differences within each 4-note block (b[1]-b[0], b[2]-b[1], b[3]-b[2]):
Block 0: diffs=[-2, -1, -1]
Block 1: diffs=[-3, 0, -2]
Block 2: diffs=[0, -4, -2]
Block 3: diffs=[0, -3, 0]
Block 4: diffs=[0, -2, -3]
Block 5: diffs=[-1, -3, -2]
Block 6: diffs=[-1, -1, -5]
Block 7: diffs=[-1, -2, -2]
Block 8: diffs=[4, 0, 2]
Block 9: diffs=[1, 2, 2]

Differences with previous note (chaining across entire song):
First 20 chain diffs: [-2, -1, -1, 5, -3, 0, -2, 5, 0, -4, -2, 5, 0, -3, 0, 3, 0, -2, -3, 6]
"""



""" THIS IS THE CORRECT IDEA OF HOW TO SOLVE """
# Check monotonicity of each 4-note block
block_directions = []
for i, b in enumerate(blocks):
	diffs = [b[j+1] - b[j] for j in range(3)]
	is_up = all(d >= 0 for d in diffs)
	is_down = all(d <= 0 for d in diffs)
	if is_up and not is_down:
		block_directions.append(('UP', diffs))
	elif is_down and not is_up:
		block_directions.append(('DOWN', diffs))
	elif is_up and is_down: # all diffs are 0
		block_directions.append(('FLAT', diffs))
	else:
		block_directions.append(('MIXED', diffs))

from collections import Counter
counts = Counter([d[0] for d in block_directions])
print("Block direction counts:", counts)

"""
OUTPUT:
Block direction counts: Counter({'UP': 152, 'DOWN': 144})
"""





def solve_challenge():
	import re

	ly_notes_text = getLyNotesText("../dist/DirectionalSlopes_4ppb_7div_Noise.ly")


	note_map = {"c'": 0, "d'": 1, "e'": 2, "f'": 3, "g'": 4, "a'": 5, "b'": 6, "c''": 7}

	# Filter out LilyPond commands (e.g. \break) and comments before extracting note tokens
	# notes = re.findall(r"[a-g][\'\']*", ly_notes_text)	# FAILS. REPLACED WITH BELOW BLOCK.
	notes = []
	for line in ly_notes_text.splitlines():
		line = re.sub(r'%.*', '', line).strip()
		if not line or line.startswith('\\'):
			continue
		for tok in line.split():
			m = re.match(r"([a-g][\'\']*)(\d*)", tok)
			if m:
				notes.append(m.group(1))
	
	vals = [note_map[n] for n in notes]

	blocks = [vals[i:i+4] for i in range(0, len(vals), 4)]

	bits = []
	for b in blocks:
		diffs = [b[j+1] - b[j] for j in range(3)]
		if all(d >= 0 for d in diffs):
			bits.append('1')
		elif all(d <= 0 for d in diffs):
			bits.append('0')

	flag = ""
	for i in range(2, len(bits)//8):
		byte_str = "".join(bits[i*8:(i+1)*8])
		flag += chr(int(byte_str, 2))

	print("Flag:", flag)

solve_challenge()
"""
Final Result
Combining all decoded characters from sections #2 through #36:
OUTPUT:
flag{sl0p3s_N_D3r1v4t1v3s_R_Gr4T3!}
"""



