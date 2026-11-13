
lilypond_text = """
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
"""


""" Extract notes from comment-containing text. """
import re

measures = []
lines = lilypond_text.strip().split('\break')
for block in lines:
    notes = re.findall(r'([a-g][f|s]*\'?4?)', block)
    if notes:
        # clean note names (remove duration '4' and octaves '\'')
        cleaned = [re.sub(r'[4\']', '', n) for n in notes]
        measures.append(cleaned)

print(f"\nTotal # of measures: {len(measures)}\n")
print("Octave-independent notes in each measure:")
for i, m in enumerate(measures):
    print(f"Measure #{i:2d}: {m}")
print("\n\n")

"""
Code output
Total measures: 44
# 0: ['c', 'e', 'b', 'a', 'g', 'f', 'e', 'c']
# 1: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'ef', 'c']
# 2: ['c', 'ef', 'bf', 'a', 'gf', 'fs', 'e', 'c']
# 3: ['c', 'ef', 'bf', 'a', 'g', 'f', 'e', 'cs']
# 4: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'ef', 'cs']
# 5: ['c', 'ef', 'bf', 'af', 'gf', 'f', 'ef', 'cs']
# 6: ['c', 'ef', 'bf', 'a', 'g', 'f', 'ef', 'c']
# 7: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs']
# 8: ['c', 'ef', 'bf', 'af', 'g', 'fs', 'e', 'c']
# 9: ['c', 'ef', 'bf', 'af', 'g', 'fs', 'ef', 'cs']
#10: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs']
#11: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'cs']
#12: ['c', 'e', 'bf', 'af', 'g', 'f', 'ef', 'cs']
#13: ['c', 'ef', 'b', 'af', 'gf', 'fs', 'ef', 'cs']
#14: ['c', 'ef', 'bf', 'a', 'gf', 'fs', 'e', 'cs']
#15: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'c']
#16: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'e', 'c']
#17: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs']
#18: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'ef', 'c']
#19: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs']
#20: ['c', 'ef', 'bf', 'a', 'g', 'f', 'ef', 'cs']
#21: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'c']
#22: ['c', 'ef', 'bf', 'af', 'g', 'fs', 'e', 'c']
#23: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs']
#24: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'c']
#25: ['c', 'ef', 'bf', 'a', 'gf', 'fs', 'ef', 'c']
#26: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'cs']
#27: ['c', 'ef', 'b', 'af', 'gf', 'fs', 'ef', 'cs']
#28: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'ef', 'c']
#29: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'c']
#30: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'c']
#31: ['c', 'ef', 'bf', 'a', 'gf', 'fs', 'e', 'cs']
#32: ['c', 'ef', 'b', 'af', 'gf', 'fs', 'ef', 'cs']
#33: ['c', 'ef', 'bf', 'af', 'g', 'fs', 'e', 'c']
#34: ['c', 'ef', 'bf', 'a', 'gf', 'f', 'e', 'c']
#35: ['c', 'e', 'bf', 'af', 'g', 'f', 'ef', 'cs']
#36: ['c', 'ef', 'b', 'af', 'gf', 'fs', 'ef', 'cs']
#37: ['c', 'ef', 'bf', 'af', 'g', 'f', 'e', 'c']
#38: ['c', 'ef', 'bf', 'a', 'gf', 'f', 'e', 'c']
#39: ['c', 'ef', 'bf', 'af', 'g', 'f', 'ef', 'c']
#40: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'c']
#41: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'cs']
#42: ['c', 'e', 'bf', 'af', 'g', 'f', 'ef', 'cs']
#43: ['c', 'ef', 'bf', 'af', 'gf', 'fs', 'e', 'cs']
"""










pitch_map = {
    'c': 0, 'cs': 1, 'df': 1, 'd': 2, 'ds': 3, 'ef': 3,
    'e': 4, 'f': 5, 'fs': 6, 'gf': 6, 'g': 7, 'gs': 8,
    'af': 8, 'a': 9, 'as': 10, 'bf': 10, 'b': 11
}

parsed_measures = []
for m in measures:
    parsed_measures.append([pitch_map[n] for n in m])

print("Notes names as integer distances from note `c` (sharps are non-negligible in distance values):")
for i, pm in enumerate(parsed_measures):
    print(f"Measure #{i:2d}: {pm}")
print("\n\n")
"""
Code output
# 0: [0, 4, 11, 9, 7, 5, 4, 0]
# 1: [0, 3, 10, 9, 7, 6, 3, 0]
# 2: [0, 3, 10, 9, 6, 6, 4, 0]
# 3: [0, 3, 10, 9, 7, 5, 4, 1]
# 4: [0, 3, 10, 9, 7, 6, 3, 1]
# 5: [0, 3, 10, 8, 6, 5, 3, 1]
# 6: [0, 3, 10, 9, 7, 5, 3, 0]
# 7: [0, 4, 10, 8, 7, 5, 4, 1]
# 8: [0, 3, 10, 8, 7, 6, 4, 0]
# 9: [0, 3, 10, 8, 7, 6, 3, 1]
#10: [0, 4, 10, 8, 7, 5, 4, 1]
#11: [0, 4, 10, 8, 7, 6, 4, 1]
#12: [0, 4, 10, 8, 7, 5, 3, 1]
#13: [0, 3, 11, 8, 6, 6, 3, 1]
#14: [0, 3, 10, 9, 6, 6, 4, 1]
#15: [0, 4, 10, 8, 7, 5, 4, 0]
#16: [0, 3, 10, 9, 7, 6, 4, 0]
#17: [0, 4, 10, 8, 7, 5, 4, 1]
#18: [0, 3, 10, 9, 7, 6, 3, 0]
#19: [0, 4, 10, 8, 7, 5, 4, 1]
#20: [0, 3, 10, 9, 7, 5, 3, 1]
#21: [0, 4, 10, 8, 7, 6, 4, 0]
#22: [0, 3, 10, 8, 7, 6, 4, 0]
#23: [0, 4, 10, 8, 7, 5, 4, 1]
#24: [0, 4, 10, 8, 7, 5, 4, 0]
#25: [0, 3, 10, 9, 6, 6, 3, 0]
#26: [0, 4, 10, 8, 7, 6, 4, 1]
#27: [0, 3, 11, 8, 6, 6, 3, 1]
#28: [0, 3, 10, 9, 7, 6, 3, 0]
#29: [0, 4, 10, 8, 7, 6, 4, 0]
#30: [0, 4, 10, 8, 7, 5, 4, 0]
#31: [0, 3, 10, 9, 6, 6, 4, 1]
#32: [0, 3, 11, 8, 6, 6, 3, 1]
#33: [0, 3, 10, 8, 7, 6, 4, 0]
#34: [0, 3, 10, 9, 6, 5, 4, 0]
#35: [0, 4, 10, 8, 7, 5, 3, 1]
#36: [0, 3, 11, 8, 6, 6, 3, 1]
#37: [0, 3, 10, 8, 7, 5, 4, 0]
#38: [0, 3, 10, 9, 6, 5, 4, 0]
#39: [0, 3, 10, 8, 7, 5, 3, 0]
#40: [0, 4, 10, 8, 7, 6, 4, 0]
#41: [0, 4, 10, 8, 7, 6, 4, 1]
#42: [0, 4, 10, 8, 7, 5, 3, 1]
#43: [0, 3, 10, 8, 6, 6, 4, 1]
"""









m0 = measures[0]
print("Integer differences between Measure#0's notes and EACH measure that comes after Measure#0:")
print(f"/!\\  [BASELINE]\nMeasure  #0: {m0}\n")

for i in range(1, len(measures)):
    diffs = []
    for j in range(8):
        n0 = m0[j]	# Baseline/reference measure to compare all other measures against.
        ni = measures[i][j]
        diffs.append((n0, ni))
    # Only show the notes that are different from the respective note in the baseline/reference measure.
    print(f"Measure #{i:2d}: {str(measures[i]):{6*8+2}}| diffs: {[(d[0], d[1]) for d in diffs if d[0] != d[1]]}")
print("\n\n")

"""
Code output
m0: ['c', 'e', 'b', 'a', 'g', 'f', 'e', 'c']
# 1: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'ef', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('f', 'fs'), ('e', 'ef')]
# 2: ['c', 'ef', 'bf', 'a', 'gf', 'fs', 'e', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('g', 'gf'), ('f', 'fs')]
# 3: ['c', 'ef', 'bf', 'a', 'g', 'f', 'e', 'cs'] | diffs: [('e', 'ef'), ('b', 'bf'), ('c', 'cs')]
# 4: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'ef', 'cs'] | diffs: [('e', 'ef'), ('b', 'bf'), ('f', 'fs'), ('e', 'ef'), ('c', 'cs')]
# 5: ['c', 'ef', 'bf', 'af', 'gf', 'f', 'ef', 'cs'] | diffs: [('e', 'ef'), ('b', 'bf'), ('a', 'af'), ('g', 'gf'), ('e', 'ef'), ('c', 'cs')]
# 6: ['c', 'ef', 'bf', 'a', 'g', 'f', 'ef', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('e', 'ef')]
# 7: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('c', 'cs')]
# 8: ['c', 'ef', 'bf', 'af', 'g', 'fs', 'e', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('a', 'af'), ('f', 'fs')]
# 9: ['c', 'ef', 'bf', 'af', 'g', 'fs', 'ef', 'cs'] | diffs: [('e', 'ef'), ('b', 'bf'), ('a', 'af'), ('f', 'fs'), ('e', 'ef'), ('c', 'cs')]
#10: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('c', 'cs')]
#11: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('f', 'fs'), ('c', 'cs')]
#12: ['c', 'e', 'bf', 'af', 'g', 'f', 'ef', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('e', 'ef'), ('c', 'cs')]
#13: ['c', 'ef', 'b', 'af', 'gf', 'fs', 'ef', 'cs'] | diffs: [('e', 'ef'), ('a', 'af'), ('g', 'gf'), ('f', 'fs'), ('e', 'ef'), ('c', 'cs')]
#14: ['c', 'ef', 'bf', 'a', 'gf', 'fs', 'e', 'cs'] | diffs: [('e', 'ef'), ('b', 'bf'), ('g', 'gf'), ('f', 'fs'), ('c', 'cs')]
#15: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'c'] | diffs: [('b', 'bf'), ('a', 'af')]
#16: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'e', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('f', 'fs')]
#17: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('c', 'cs')]
#18: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'ef', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('f', 'fs'), ('e', 'ef')]
#19: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('c', 'cs')]
#20: ['c', 'ef', 'bf', 'a', 'g', 'f', 'ef', 'cs'] | diffs: [('e', 'ef'), ('b', 'bf'), ('e', 'ef'), ('c', 'cs')]
#21: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'c'] | diffs: [('b', 'bf'), ('a', 'af'), ('f', 'fs')]
#22: ['c', 'ef', 'bf', 'af', 'g', 'fs', 'e', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('a', 'af'), ('f', 'fs')]
#23: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('c', 'cs')]
#24: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'c'] | diffs: [('b', 'bf'), ('a', 'af')]
#25: ['c', 'ef', 'bf', 'a', 'gf', 'fs', 'ef', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('g', 'gf'), ('f', 'fs'), ('e', 'ef')]
#26: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('f', 'fs'), ('c', 'cs')]
#27: ['c', 'ef', 'b', 'af', 'gf', 'fs', 'ef', 'cs'] | diffs: [('e', 'ef'), ('a', 'af'), ('g', 'gf'), ('f', 'fs'), ('e', 'ef'), ('c', 'cs')]
#28: ['c', 'ef', 'bf', 'a', 'g', 'fs', 'ef', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('f', 'fs'), ('e', 'ef')]
#29: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'c'] | diffs: [('b', 'bf'), ('a', 'af'), ('f', 'fs')]
#30: ['c', 'e', 'bf', 'af', 'g', 'f', 'e', 'c'] | diffs: [('b', 'bf'), ('a', 'af')]
#31: ['c', 'ef', 'bf', 'a', 'gf', 'fs', 'e', 'cs'] | diffs: [('e', 'ef'), ('b', 'bf'), ('g', 'gf'), ('f', 'fs'), ('c', 'cs')]
#32: ['c', 'ef', 'b', 'af', 'gf', 'fs', 'ef', 'cs'] | diffs: [('e', 'ef'), ('a', 'af'), ('g', 'gf'), ('f', 'fs'), ('e', 'ef'), ('c', 'cs')]
#33: ['c', 'ef', 'bf', 'af', 'g', 'fs', 'e', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('a', 'af'), ('f', 'fs')]
#34: ['c', 'ef', 'bf', 'a', 'gf', 'f', 'e', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('g', 'gf')]
#35: ['c', 'e', 'bf', 'af', 'g', 'f', 'ef', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('e', 'ef'), ('c', 'cs')]
#36: ['c', 'ef', 'b', 'af', 'gf', 'fs', 'ef', 'cs'] | diffs: [('e', 'ef'), ('a', 'af'), ('g', 'gf'), ('f', 'fs'), ('e', 'ef'), ('c', 'cs')]
#37: ['c', 'ef', 'bf', 'af', 'g', 'f', 'e', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('a', 'af')]
#38: ['c', 'ef', 'bf', 'a', 'gf', 'f', 'e', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('g', 'gf')]
#39: ['c', 'ef', 'bf', 'af', 'g', 'f', 'ef', 'c'] | diffs: [('e', 'ef'), ('b', 'bf'), ('a', 'af'), ('e', 'ef')]
#40: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'c'] | diffs: [('b', 'bf'), ('a', 'af'), ('f', 'fs')]
#41: ['c', 'e', 'bf', 'af', 'g', 'fs', 'e', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('f', 'fs'), ('c', 'cs')]
#42: ['c', 'e', 'bf', 'af', 'g', 'f', 'ef', 'cs'] | diffs: [('b', 'bf'), ('a', 'af'), ('e', 'ef'), ('c', 'cs')]
#43: ['c', 'ef', 'bf', 'af', 'gf', 'fs', 'e', 'cs'] | diffs: [('e', 'ef'), ('b', 'bf'), ('a', 'af'), ('g', 'gf')
"""









print("\n----  Testing whether alteredPitch is supposed to represent bitValue1 vs bitValue0 (also accounting for endianness)  ----")
print("(The created string that makes sense is likely the correct interpretation)")
# Let's inspect each measure as 8 bits.
# Let's see what happens if modified (altered) = 1, natural = 0 (or vice versa)

bytes_alt1 = []
bytes_alt0 = []

for i in range(1, len(measures)):
    m = measures[i]
    m0 = measures[0]
    
    # Version 1: Assume `1` if altered (i.e., goes from natural in baseline measure, to flat or sharp), `0` if exact matching pitch
    bits1 = [1 if m[j] != m0[j] else 0 for j in range(8)]
    val1 = int(''.join(map(str, bits1)), 2)
    bytes_alt1.append(val1)
    
    # Version 2: Assume `0` if altered, `1` if identical note name
    bits0 = [0 if m[j] != m0[j] else 1 for j in range(8)]
    val0 = int(''.join(map(str, bits0)), 2)
    bytes_alt0.append(val0)

print("Altered = 1:")
bytes_alt1_rev = []
for i in range(1, len(measures)):
    m = measures[i]
    m0 = measures[0]
    bits1 = [1 if m[j] != m0[j] else 0 for j in range(8)]
    val1 = int(''.join(map(str, bits1[::-1])), 2)
    bytes_alt1_rev.append(val1)
print("* MSB-first:", bytes(bytes_alt1))
print("* LSB-first:", bytes(bytes_alt1_rev), "\n")

print("Altered = 0:")
bytes_alt0_rev = []
for i in range(1, len(measures)):
    m = measures[i]
    m0 = measures[0]
    bits0 = [0 if m[j] != m0[j] else 1 for j in range(8)]
    val0 = int(''.join(map(str, bits0[::-1])), 2)
    bytes_alt0_rev.append(val0)
print("* MSB-first:", bytes(bytes_alt0))
print("* LSB-first:", bytes(bytes_alt0_rev), "\n")
print("\n\n")

r"""
Code output
Altered = 1, MSB-first:
b'flag{b1tw153_m0d1f1c4t10n5_f40m_th3_phr453}'
Altered = 1, LSB-first:
b'f6\x86\xe6\xdeF\x8c.\xee\x8c\xac\xcc\xfa\xb6\x0c&\x8cf\x8c\xc6,.\x8c\x0cv\xac\xfaf,\x0c\
"""








print("bitstring -> integer -> ASCII char")
res = []
for i, m in enumerate(measures):
    # If m0 is the baseline, what is m0 itself? All zeros -> byte 0.
    # But wait, what if we check the bits relative to 'c e b a g f e c'?
    # Note 0: c (natural) vs cs (sharp) -> 0 vs 1
    # Note 1: e vs ef -> 0 vs 1
    # Note 2: b vs bf -> 0 vs 1
    # Note 3: a vs af -> 0 vs 1
    # Note 4: g vs gf -> 0 vs 1
    # Note 5: f vs fs -> 0 vs 1
    # Note 6: e vs ef -> 0 vs 1
    # Note 7: c vs cs -> 0 vs 1
    
    bits = [1 if m[j] != m0[j] else 0 for j in range(8)]
    val = int(''.join(map(str, bits)), 2)
    res.append((i, val, chr(val) if 32 <= val <= 126 else repr(chr(val))))

for r in res:
    print(f"Measure {r[0]:2d}: bits={[1 if measures[r[0]][j] != m0[j] else 0 for j in range(8)]} -> {r[1]:3d} = {r[2]}")
print("\n\n")
"""
Code output
Measure  0: bits=[0, 0, 0, 0, 0, 0, 0, 0] ->   0 = '\x00'
Measure  1: bits=[0, 1, 1, 0, 0, 1, 1, 0] -> 102 = f
Measure  2: bits=[0, 1, 1, 0, 1, 1, 0, 0] -> 108 = l
Measure  3: bits=[0, 1, 1, 0, 0, 0, 0, 1] ->  97 = a
Measure  4: bits=[0, 1, 1, 0, 0, 1, 1, 1] -> 103 = g
Measure  5: bits=[0, 1, 1, 1, 1, 0, 1, 1] -> 123 = {
Measure  6: bits=[0, 1, 1, 0, 0, 0, 1, 0] ->  98 = b
Measure  7: bits=[0, 0, 1, 1, 0, 0, 0, 1] ->  49 = 1
Measure  8: bits=[0, 1, 1, 1, 0, 1, 0, 0] -> 116 = t
Measure  9: bits=[0, 1, 1, 1, 0, 1, 1, 1] -> 119 = w
Measure 10: bits=[0, 0, 1, 1, 0, 0, 0, 1] ->  49 = 1
Measure 11: bits=[0, 0, 1, 1, 0, 1, 0, 1] ->  53 = 5
Measure 12: bits=[0, 0, 1, 1, 0, 0, 1, 1] ->  51 = 3
Measure 13: bits=[0, 1, 0, 1, 1, 1, 1, 1] ->  95 = _
Measure 14: bits=[0, 1, 1, 0, 1, 1, 0, 1] -> 109 = m
Measure 15: bits=[0, 0, 1, 1, 0, 0, 0, 0] ->  48 = 0
Measure 16: bits=[0, 1, 1, 0, 0, 1, 0, 0] -> 100 = d
Measure 17: bits=[0, 0, 1, 1, 0, 0, 0, 1] ->  49 = 1
Measure 18: bits=[0, 1, 1, 0, 0, 1, 1, 0] -> 102 = f
Measure 19: bits=[0, 0, 1, 1, 0, 0, 0, 1] ->  49 = 1
Measure 20: bits=[0, 1, 1, 0, 0, 0, 1, 1] ->  99 = c
Measure 21: bits=[0, 0, 1, 1, 0, 1, 0, 0] ->  52 = 4
Measure 22: bits=[0, 1, 1, 1, 0, 1, 0, 0] -> 116 = t
Measure 23: bits=[0, 0, 1, 1, 0, 0, 0, 1] ->  49 = 1
Measure 24: bits=[0, 0, 1, 1, 0, 0, 0, 0] ->  48 = 0
Measure 25: bits=[0, 1, 1, 0, 1, 1, 1, 0] -> 110 = n
Measure 26: bits=[0, 0, 1, 1, 0, 1, 0, 1] ->  53 = 5
Measure 27: bits=[0, 1, 0, 1, 1, 1, 1, 1] ->  95 = _
Measure 28: bits=[0, 1, 1, 0, 0, 1, 1, 0] -> 102 = f
Measure 29: bits=[0, 0, 1, 1, 0, 1, 0, 0] ->  52 = 4
Measure 30: bits=[0, 0, 1, 1, 0, 0, 0, 0] ->  48 = 0
Measure 31: bits=[0, 1, 1, 0, 1, 1, 0, 1] -> 109 = m
Measure 32: bits=[0, 1, 0, 1, 1, 1, 1, 1] ->  95 = _
Measure 33: bits=[0, 1, 1, 1, 0, 1, 0, 0] -> 116 = t
Measure 34: bits=[0, 1, 1, 0, 1, 0, 0, 0] -> 104 = h
Measure 35: bits=[0, 0, 1, 1, 0, 0, 1, 1] ->  51 = 3
Measure 36: bits=[0, 1, 0, 1, 1, 1, 1, 1] ->  95 = _
Measure 37: bits=[0, 1, 1, 1, 0, 0, 0, 0] -> 112 = p
Measure 38: bits=[0, 1, 1, 0, 1, 0, 0, 0] -> 104 = h
Measure 39: bits=[0, 1, 1, 1, 0, 0, 1, 0] -> 114 = r
Measure 40: bits=[0, 0, 1, 1, 0, 1, 0, 0] ->  52 = 4
Measure 41: bits=[0, 0, 1, 1, 0, 1, 0, 1] ->  53 = 5
Measure 42: bits=[0, 0, 1, 1, 0, 0, 1, 1] ->  51 = 3
Measure 43: bits=[0, 1, 1, 1, 1, 1, 0, 1] -> 125 = }

Flag: flag{b1tw153_m0d1f1c4t10n5_f40m_th3_phr453}
"""
















import re

lilypond_source = """
% Insert LilyPond content here
"""

def solve_lilypond(source_text: str) -> str:
    # Measure 0 reference notes
    base_measure = ['c', 'e', 'b', 'a', 'g', 'f', 'e', 'c']
    
    # Extract measures by split on \break
    blocks = source_text.split(r'\break')
    
    flag_chars = []
    
    for block in blocks:
        # Match note names (ignoring octaves and durations)
        notes = re.findall(r'([a-g][f|s]*)', block)
        if len(notes) == 8:
            # Compare each note against the base measure
            bits = [1 if notes[i] != base_measure[i] else 0 for i in range(8)]
            
            # Convert binary array to integer
            char_code = int(''.join(map(str, bits)), 2)
            
            # Skip baseline measure 0 (all 0s)
            if char_code > 0:
                flag_chars.append(chr(char_code))
                
    return "".join(flag_chars)

if __name__ == "__main__":
    # If loading from file:
    with open("../dist/IttyBittyDifferences.ly", "r", encoding="utf-8") as f:
        content = f.read()
    print("Decoded Flag:", solve_lilypond(content))







