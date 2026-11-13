# Decode a WaveCode 2 CSV using only the public encoding specification.
import argparse
import cmath
import csv
import math
from pathlib import Path

challengeRoot = Path(__file__).resolve().parents[1]
argumentParser = argparse.ArgumentParser(description='Decode a WaveCode 2 transmission.')
argumentParser.add_argument('csvPath', nargs='?', type=Path,
                            default=challengeRoot / 'dist' / 'beacon.csv')
scriptArguments = argumentParser.parse_args()
with scriptArguments.csvPath.open(newline='') as inputFile:
    sampleRows = list(csv.DictReader(inputFile))
sampleTimes = [float(sampleRow['timeSeconds']) for sampleRow in sampleRows]
sampleValues = [float(sampleRow['amplitude']) for sampleRow in sampleRows]
sampleCount = len(sampleValues)
if sampleCount < 2 or sampleCount & (sampleCount - 1):
    raise ValueError('Expected a power-of-two sample count of at least two')
sampleInterval = (sampleTimes[-1] - sampleTimes[0]) / (sampleCount - 1)
if sampleInterval <= 0:
    raise ValueError('Expected increasing timestamps')
for sampleIndex in range(1, sampleCount):
    if not math.isclose(sampleTimes[sampleIndex] - sampleTimes[sampleIndex - 1],
                        sampleInterval, rel_tol=1e-7, abs_tol=1e-12):
        raise ValueError('Expected uniform sample spacing')
sampleRate = 1 / sampleInterval
spectrum = [complex(sampleValue) for sampleValue in sampleValues]

# Reverse the index bits, then combine successively larger FFT groups.
reversedIndex = 0
for sampleIndex in range(1, sampleCount):
    indexBit = sampleCount >> 1
    while reversedIndex & indexBit:
        reversedIndex ^= indexBit
        indexBit >>= 1
    reversedIndex ^= indexBit
    if sampleIndex < reversedIndex:
        spectrum[sampleIndex], spectrum[reversedIndex] = spectrum[reversedIndex], spectrum[sampleIndex]
blockSize = 2
while blockSize <= sampleCount:
    halfSize = blockSize // 2
    phaseStep = cmath.exp(-2j * math.pi / blockSize)
    for blockStart in range(0, sampleCount, blockSize):
        phaseFactor = 1 + 0j
        for offsetIndex in range(halfSize):
            evenIndex = blockStart + offsetIndex
            oddIndex = evenIndex + halfSize
            evenValue = spectrum[evenIndex]
            oddValue = phaseFactor * spectrum[oddIndex]
            spectrum[evenIndex] = evenValue + oddValue
            spectrum[oddIndex] = evenValue - oddValue
            phaseFactor *= phaseStep
    blockSize *= 2

# Read the nine-symbol header, then the declared number of payload symbols.
frameText = ''
frameLength = 9
symbolIndex = 0
while symbolIndex < frameLength:
    frequency = 8 + 4 * symbolIndex
    if frequency >= sampleRate / 2:
        raise ValueError('Frame exceeds available frequency slots')
    binPosition = frequency * sampleCount / sampleRate
    binIndex = round(binPosition)
    if not math.isclose(binPosition, binIndex, abs_tol=1e-6):
        raise ValueError('Expected bin-aligned frequencies')
    symbolEstimate = 128 * 2 * abs(spectrum[binIndex]) / sampleCount
    symbolValue = round(symbolEstimate)
    if not 0 <= symbolValue <= 127 or abs(symbolEstimate - symbolValue) > 0.01:
        raise ValueError('Invalid ASCII amplitude')
    frameText += chr(symbolValue)
    symbolIndex += 1
    if symbolIndex == 9:
        if frameText[:4] != 'WC2:' or frameText[8] != ':':
            raise ValueError('Invalid frame header')
        frameLength += int(frameText[4:8], 16)
packetText = frameText[9:]
print(packetText, end='')
