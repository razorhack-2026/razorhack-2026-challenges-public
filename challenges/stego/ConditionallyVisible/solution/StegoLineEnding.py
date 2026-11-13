import textwrap
from random import randint
from math import ceil


STEGOTEXT_FOR_0, DEBUGTEXT_FOR_0  =  ' ',  '~'
STEGOTEXT_FOR_1, DEBUGTEXT_FOR_1  =  '\t', '$'

def makeBitstringReadable(bitstring:str, USE_7BITS_PER_CHAR:bool) -> str:
	NUM_BITS_PER_CHAR  =  7 if USE_7BITS_PER_CHAR  else 8
	formattedBitstring = ""
	for bit_idx, bit in enumerate(bitstring):
		if (bit_idx%NUM_BITS_PER_CHAR == NUM_BITS_PER_CHAR-1) and (bit_idx!=0) and (bit_idx != len(bitstring)-1):
			formattedBitstring += (bit+"__")
		else:
			formattedBitstring += bit
	return formattedBitstring


def text_to_binary(secret_string: str, USE_7BITS_PER_CHAR: bool, DEBUG: bool = True) -> str:
	""" Converts a plaintext string into binary ASCII/UTF-8 values (8 bits per byte) or ASCII/UTF-7 values (7 bits per byte). """
	bitstring = ""
	if USE_7BITS_PER_CHAR:
		bitstring = ''.join(f"{byte:07b}" for byte in secret_string.encode('utf-7'))
	else:
		bitstring = ''.join(f"{byte:08b}" for byte in secret_string.encode('utf-8'))
	
	if DEBUG:
		print("\ntext_to_binary():\n* bitstring:", bitstring)
		formattedBitstring = makeBitstringReadable(bitstring, USE_7BITS_PER_CHAR)
		print("* formattedBitstring:", formattedBitstring)
	return bitstring



def parseEssayIntoLines__plainTerminalWidth(essay_text: str, widthPerLine: int = 80, DEBUG: bool = True) -> list[str]:
	essayLen = len(essay_text)
	numLines = essayLen//widthPerLine
	lines = [essay_text[i:i+widthPerLine] for i in range(numLines)]
	if DEBUG:
		print("\nparseEssayIntoLines__plainTerminalWidth():\nLines:")
		[print(f"Line #{idx})\n{p}\n") for idx,p in enumerate(lines,1)]
	return lines

def parseEssayIntoLines__fancyLib(essay_text: str, widthPerLine: int = 60, DEBUG: bool = True) -> list[str]:
	"""
	Parses essay text using word-wrap logic similar to text editors (e.g. Word).
	Keeps whole words and attached punctuation intact without isolated single-character 
	punctuation lines.
	"""

	paragraphs = essay_text.splitlines()
	if DEBUG:
		print("parseEssayIntoLines__fancyLib():\nParagraphs:")
		[print(f"Para #{idx})\n{p}\n") for idx,p in enumerate(paragraphs,1)]
	
	lines = []
	wrapper = textwrap.TextWrapper(
		width=widthPerLine,
		break_long_words=False,
		break_on_hyphens=True,
		replace_whitespace=True
	)
	
	for idxP,p in enumerate(paragraphs, 1):
		cleaned_p = p.strip()   # Strip leading&trailing whitespace
		if cleaned_p:
			wrapped_lines = wrapper.wrap(cleaned_p)
			if DEBUG:
				print(f"\nparseEssayIntoLines__fancyLib():\nPara #{idxP}) wrapped_lines:")
				[print(f"  Line #{idxL}) {wl}") for idxL,wl in enumerate(wrapped_lines,1)]
			lines.extend(wrapped_lines)
			
	return lines


def parseEssayIntoLines(LINE_WIDTH:int, filenameOfEssay:str = None, essayTextAsStr:str = None, DEBUG:bool = True) -> str:
	READ_FROM_FILE = (filenameOfEssay is not None)
	USE_PROVIDED_TEXT = (essayTextAsStr is not None)
	assert READ_FROM_FILE ^ USE_PROVIDED_TEXT, \
		"[ERROR]  Expected exactly ONE of either `filenameOfEssay` or `essayTextAsStr` to be None (and the other variable to *not* be None)."
	if READ_FROM_FILE:
		sample_essay = ""
		OPT_READ_BIN = "rb"
		OPT_READ_TEXT = "rt"
		try:
			with open(filenameOfEssay, OPT_READ_TEXT) as myFile:
				essayTextAsStrFromFile = myFile.read()
			print(f"[INFO]  Read {len(essayTextAsStrFromFile):,} bytes from file \"{filenameOfEssay}\".")
		except Exception as e:
			raise FileNotFoundError(e + f"Are you sure your file is in the correct folder? SoughtFile=\"{filenameOfEssay}\"")
		
		parsedLines = parseEssayIntoLines__fancyLib(essayTextAsStrFromFile, LINE_WIDTH, DEBUG)
	elif USE_PROVIDED_TEXT:
		# Use the simpler plainTerminalWidth technique since the lines should be shorter (compared to a file's numLines)
		parsedLines = parseEssayIntoLines__plainTerminalWidth(essayTextAsStr, LINE_WIDTH, DEBUG)
	else:
		raise ValueError("[ERROR]  Invalid input. Neither READ_FROM_FILE nor USE_PROVIDED_TEXT were True.")
	
	if DEBUG:
		print("[DEBUG]  Essay that has been parsed into lines (up to first 64 lines are shown):")
		for i, line in enumerate(parsedLines, 1):
			if i<64:
				print(f"Line #{i:2d}: {line}")
			else:
				break	# Exit the for loop after printing a bunch of lines of covertext.
	return parsedLines


def encode_stego_text(filenameOfNonstegoEssayCovertext:str, nonstegoEssayCovertext: str, secret_string: str, widthPerLine: int, max_bits_per_line: int, RANDOMIZE_BPL: bool, USE_7BITS_PER_CHAR: bool, DEBUG: bool) -> str:
	"""
	Embeds secret_string into nonstegoEssayCovertext using trailing: spaces (' ' / '~') for 0, and tabs ('\t' / '$') for 1.
	Appends a maximum of `bits_per_line` (ideally just 1 or 2) whitespace characters before each line break.
	Verifies that the text contains enough lines to fit the payload.
	"""
	
	MIN_BITS_PER_LINE, MAX_BITS_PER_LINE  =  1, 3
	if max_bits_per_line not in      range(MIN_BITS_PER_LINE, MAX_BITS_PER_LINE+1):
		s = "".join([f" or {n}"     for n in range(MIN_BITS_PER_LINE, MAX_BITS_PER_LINE+1)])
		raise ValueError(f"max_bits_per_line must be {MIN_BITS_PER_LINE}{s}.  This is enforced to make detection less likely.")

	# Step 1: Word-wrap essay into clean lines
	linesCovertext = parseEssayIntoLines(LINE_WIDTH, filenameOfNonstegoEssayCovertext, nonstegoEssayCovertext, DEBUG = False)

	# Ensure there's no ambiguity as to how many characters to read from the end of the line leftward.
	linesCovertext = [line.rstrip(STEGOTEXT_FOR_0).rstrip(STEGOTEXT_FOR_1).rstrip(DEBUGTEXT_FOR_0).rstrip(DEBUGTEXT_FOR_1)    for line in linesCovertext]
	
	# Step 2: Convert plaintext string to binary ASCII
	bitstring = text_to_binary(secret_string, USE_7BITS_PER_CHAR=USE_7BITS_PER_CHAR, DEBUG=DEBUG)
	total_bits = len(bitstring)
	
	# Step 3: Verify line capacity (2 bits per line max)
	sum_numBitsPerLinePlannedSoFar = 0
	if RANDOMIZE_BPL:
		list_numBitsPerLine = []
		while sum_numBitsPerLinePlannedSoFar < total_bits:
			# max_bits_per_line-1 shifts the average down by 1 so that I can add the max random value and not exceed the user-established value for max_bits_per_line.
			numBitsPerLine = max(1, max_bits_per_line-1 + randint(-1,1))    # Vary the # of bitsPerLine by +1 or -1 (or keep it the same!)

			list_numBitsPerLine.append(numBitsPerLine)
			sum_numBitsPerLinePlannedSoFar += numBitsPerLine
		num_required_lines = len(list_numBitsPerLine)
	else:
		# if Use the same # of bits per line   for EVERY line.
		# `max_bits_per_line - 1` allows for requiring (a max of exactly) one more line after all the prior lines, mitigating one-line-too-few errors.
		# * Though, I'm still not sure this formula is actually correct...
		num_required_lines = (total_bits + max_bits_per_line - 1) // max_bits_per_line
	
	num_available_linesCovertext = len(linesCovertext)
	
	if RANDOMIZE_BPL:
		numBitsSuccessfullyEncoded = min(total_bits, sum( list_numBitsPerLine[0:num_available_linesCovertext] ))	# min(total_bits, ...) caps the #bits because the list's last quantity can exceed the #bits *actually* encoded.
	else:
		numBitsSuccessfullyEncoded = min(total_bits,  max_bits_per_line * num_available_linesCovertext)
	print("numCharsSuccessfullyEncoded =", len(secret_string))
	print("numBitsSuccessfullyEncoded =", numBitsSuccessfullyEncoded)
	numRemainingBitsReqd        =  total_bits - numBitsSuccessfullyEncoded
	print("numRemainingBitsReqd =", numRemainingBitsReqd)
	maxNumReqdExtraLines = ceil(numRemainingBitsReqd/MIN_BITS_PER_LINE)	# extraLinesReqd_minRand
	minNumReqdExtraLines = ceil(numRemainingBitsReqd/MAX_BITS_PER_LINE)	# extraLinesReqd_maxRand
	print("minNumReqdExtraLines =", minNumReqdExtraLines)
	if (numRemainingBitsReqd != 0) or (minNumReqdExtraLines > 0) or (num_available_linesCovertext < num_required_lines):
		if RANDOMIZE_BPL:
			disclaimer  = f"- list_#BitsPerLine={list_numBitsPerLine} -> Supports up to {sum_numBitsPerLinePlannedSoFar} bits, spread across {len(list_numBitsPerLine)} lines.\n"
			disclaimer += f"- Given the already-computed random #s, you need anywhere from {minNumReqdExtraLines} (assuming highest rand value for each added line) to {maxNumReqdExtraLines} (assuming lowest rand value for each added line) MORE lines.\n"
		else:
			disclaimer  = f"- At {max_bits_per_line} MaxBits Per PlaintextLine, you need at least {num_required_lines} plaintext lines.\n"
			disclaimer += f"  This means you need to add {num_required_lines - num_available_linesCovertext} more lines.\n"

		overallErrorStr = \
			f"Insufficient text capacity!\n"\
			f"- Payload size: {len(secret_string)} characters = {total_bits} bits.\n"\
			f"  Only {numBitsSuccessfullyEncoded} bits, spread across just {num_available_linesCovertext} lines, were encoded successfully.\n"\
			f"{disclaimer}"\
			f"- Current text at wrap widthPerLine={widthPerLine} only provides {num_available_linesCovertext} lines.\n"\
			f"Fix: To generate more lines, A) Provide more text or B) Lower the 'widthPerLine' (e.g. widthPerLine=40) or C) Skew the random numbers towards larger #s of bits to append to each line or D) Increase the # of hidden bits per line."
		raise ValueError(overallErrorStr)

	# Step 4: Append binary whitespace to end of lines
	encoded_stegolines, encoded_debuglines  =  [], []
	# histogram_numBitsPerLine = {"0":0, "1":0, "2":0, "3":0, ...}
	histogram_numBitsPerLine = {str(nBPL):0  for nBPL in range(max_bits_per_line+2)}
	bit_idx = 0
	
	for line_idx, line in enumerate(linesCovertext):
		trailing_ws_stego, trailing_ws_debug  =  "", ""
		if not RANDOMIZE_BPL:
			numBitsPerLine = max_bits_per_line
		else:
			# ATTEMPT #1
			# # max_bits_per_line-1 shifts the average down by 1 so that I can add the max random value and not exceed the user-established value for max_bits_per_line.
			# numBitsPerLine = max(1, max_bits_per_line-1 + randint(-1,1))    # Vary the # of bitsPerLine by +1 or -1 (or keep it the same!)
			# ATTEMPT #2
			# Reuse the planned random bits per line computed and verified during Step 3
			numBitsPerLine = list_numBitsPerLine[line_idx] if line_idx < len(list_numBitsPerLine) else 0
		histogram_numBitsPerLine[ str(numBitsPerLine) ] += 1    # Increment the counter for that specific length.
		
		for _ in range(numBitsPerLine):
			if bit_idx < total_bits:
				bit = bitstring[bit_idx]
				assert bit in "01",  f"Invalid value for `bit`. Expected str(0) or str(1), but got \"{bit}\"."
				trailing_ws_stego  +=  STEGOTEXT_FOR_0 if bit == '0'   else STEGOTEXT_FOR_1
				trailing_ws_debug  +=  DEBUGTEXT_FOR_0 if bit == '0'   else DEBUGTEXT_FOR_1
				bit_idx += 1
		encoded_stegolines.append(line + trailing_ws_stego)
		encoded_debuglines.append(line + trailing_ws_debug)
	print("Histogram  (hiddenBitsPerLine : numTimesThisOccurred):")
	[print("* ", keyValPair)   for keyValPair in histogram_numBitsPerLine.items()]
	print("[NOTE]  The values within the dictionary should add up to equal the # of lines used.")

	if bit_idx < total_bits:
		raise ValueError(f"Encoding incomplete! Encoded only {bit_idx} of {total_bits} hidden bits.")

	stegoEncodedAsStr = '\n'.join(encoded_stegolines)
	debugEncodedAsStr = '\n'.join(encoded_debuglines)

	stegoFilename = "../dist/GuideTo_LossyAndNonlossy_PrivacyModels_T-K-L_Diff--Priv.md"	# This file contains the stegotext (version: spaces and tabs)
	debugFilename = "../solution/debug-encodedButVisibleStegotext.txt"						# This file contains the stegotext (version: ~ and $ that can be seen)
	OPT_WRITE_TEXT = "wt"
	with open(stegoFilename, OPT_WRITE_TEXT) as file:	# Do NOT write file as bytes (i.e., do NOT do "wb")
		numBytesWrittenToFile = file.write(stegoEncodedAsStr)
		print(f"[INFO]  Saved stegotext ({numBytesWrittenToFile:,} bytes) to \"{stegoFilename}\".")
	with open(debugFilename, OPT_WRITE_TEXT) as file:	# Do NOT write file as bytes (i.e., do NOT do "wb")
		numBytesWrittenToFile = file.write(debugEncodedAsStr)
		print(f"[INFO]  Saved debug(=\"visible\") version of stegotext ({numBytesWrittenToFile:,} bytes) to \"{debugFilename}\".")

	return stegoEncodedAsStr



def decode_stego_text(stego_text: str,  max_bits_per_line: int,  USE_7BITS_PER_CHAR: bool,  DEBUG: bool = True) -> str:
	""" Extracts binary whitespace from line endings and decodes it back to plaintext. """
	extracted_bits = []

	if DEBUG:
		print("decode_stego_text():")
	for line in stego_text.splitlines():
		if DEBUG:
			print("  line:", line)
		line_bits = []
		ws_count = 0    # ws == whitespace
		# Scan trailing characters from right to left, since stegotext is at the right-side end of each line.
		for char in reversed(line):
			if char == STEGOTEXT_FOR_0:
				line_bits.append('0')
				ws_count += 1
			elif char == STEGOTEXT_FOR_1:
				line_bits.append('1')
				ws_count += 1
			else:   # Upon encountering non "0"/"1" char in line.
				break
			
			if ws_count == max_bits_per_line:
				break
			elif ws_count > max_bits_per_line:
				raise ValueError("[decode_stego_text()] Exceeded the max # of bits per parsed line.")
		if DEBUG:
			print("  * Decoded list_charToBit: ", "".join(list(reversed(line_bits))), "\n")
		extracted_bits.extend(reversed(line_bits))

	binary_str = ''.join(extracted_bits)
	if DEBUG:
		print("  * Decoded bitsAsChars: ", binary_str)
		formattedBitstring = makeBitstringReadable(binary_str, USE_7BITS_PER_CHAR)
		print("  * formattedBitstring:", formattedBitstring)
	
	# Convert binary back to UTF-8 bytes
	lenPerChar  =  7 if USE_7BITS_PER_CHAR   else 8
	byte_arr = bytearray()
	numBitsThatPartiallyFillFinalChar  =  len(binary_str) % lenPerChar
	for i in range(0, len(binary_str) - numBitsThatPartiallyFillFinalChar, lenPerChar):   # start,stop, step.    stop:  Subtract by remainder bits that wouldn't combine to create a full byte's worth of bits, which would create a encodings.decode() error.
		charAsBitstring = binary_str[i:i+lenPerChar]
		binNum = int(("0" if USE_7BITS_PER_CHAR else "") + charAsBitstring,   base=2)    # Binary is "Base2"
		byte_arr.append(binNum)
		if DEBUG:
			print(f"\n  * charAsBitstring = binary_str[i : i+{lenPerChar}] =  {charAsBitstring}")
			print(f"  * {bytes(byte_arr)},\tcurr#={binNum}, currCharFrom#={chr(binNum)}")

	if USE_7BITS_PER_CHAR:
		return byte_arr.decode('utf-7', errors='replace')
	else:
		return byte_arr.decode('utf-8', errors='replace')










if __name__ == "__main__":
	# CHANGE ME! :)
	READ_FROM_FILE = True
	MAX_NUM_BITS_PER_LINE = 3
	DEBUG = False


	textAsStr, secretAsStr, LINE_WIDTH, USE_7BITS_PER_CHAR   =   "", "", 1, False
	if READ_FROM_FILE:
		# CHANGE ME! :)
		LINE_WIDTH = 160	# Use longer line widths since we have a BUNCH of text to work with, which also makes the resulting file output less suspicious.
		USE_7BITS_PER_CHAR=False		# UTF-7 vs UTF-8 (use UTF8 if you want to support many more chars than just alphanumeric)
		secretAsStr = r"flag{K-Anonymity+L-+T-[1053n3zz_I5_B3tt3R_Th4|\|_D1ff3r3|\|t141_Pr1\/4[`/_sumTimes}"

		filenameOfNonstegoEssay = "../src/noStego--GuideTo_LossyAndNonlossy_PrivacyModels_T-K-L_Diff--Priv.md"	# No stegotext exists in this file.
		sample_para = None
	
	else:
		# CHANGE ME! :)
		LINE_WIDTH = 40
		USE_7BITS_PER_CHAR=True		# UTF-7 vs UTF-8
		secretAsStr = "Hi!"  # 3 characters = 24 bits -> requires 12 lines at 2 bits/line

		filenameOfNonstegoEssay = None
		sample_para = (
			"Steganography is the practice of concealing a secret message within another ordinary file. "
			"Unlike cryptography, which conceals content, steganography hides the very fact that a secret "
			"communication is taking place. This implementation formats text cleanly using word wrapping, "
			"keeping whole words and attached punctuation intact while hiding binary bits in trailing whitespace."
		)

	

	# Commented out because I don't want all the debug text...
	# print(f"--- Word-Wrap Line Parsing Test (widthPerLine={LINE_WIDTH}) ---")
	# parsedLines_covertext = parseEssayIntoLines(LINE_WIDTH, filenameOfEssay = filenameOfNonstegoEssay, essayTextAsStr = sample_para, DEBUG = True)

	print("\n--- Encoding Stego Data ---")
	encoded = encode_stego_text(filenameOfNonstegoEssay, sample_para, secretAsStr, widthPerLine=LINE_WIDTH, max_bits_per_line=MAX_NUM_BITS_PER_LINE, RANDOMIZE_BPL=True, USE_7BITS_PER_CHAR=USE_7BITS_PER_CHAR, DEBUG=DEBUG)
	print("Encoding successful!")
	if DEBUG:
		print("\nEncoded text:")
		print("{\n"+encoded+"\n}\n")

	print("\n--- Decoding Stego Data ---")
	decoded = decode_stego_text(encoded, max_bits_per_line=MAX_NUM_BITS_PER_LINE, USE_7BITS_PER_CHAR=USE_7BITS_PER_CHAR, DEBUG=DEBUG)
	print(f"Decoded Message: '{decoded}'")

	assert decoded == secretAsStr, "Decoded payload does not match original!"