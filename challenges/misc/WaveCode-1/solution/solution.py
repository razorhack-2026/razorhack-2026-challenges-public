# Recover the dominant frequency from the competitor CSV using a radix-2 FFT.

import argparse
import cmath
import csv
import math
from pathlib import Path

challengeRoot = Path(__file__).resolve().parents[1]
argumentParser = argparse.ArgumentParser(description='Find the strongest waveform frequency.')
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
    timeDifference = sampleTimes[sampleIndex] - sampleTimes[sampleIndex - 1]
    if not math.isclose(timeDifference, sampleInterval, rel_tol=1e-7, abs_tol=1e-12):
        raise ValueError('Expected uniformly spaced timestamps')
sampleRate = 1 / sampleInterval

# Reorder the samples by reversed binary index for the iterative FFT.
spectrum = [complex(sampleValue) for sampleValue in sampleValues]
reversedIndex = 0
for sampleIndex in range(1, sampleCount):
    indexBit = sampleCount >> 1
    while reversedIndex & indexBit:
        reversedIndex ^= indexBit
        indexBit >>= 1
    reversedIndex ^= indexBit
    if sampleIndex < reversedIndex:
        spectrum[sampleIndex], spectrum[reversedIndex] = spectrum[reversedIndex], spectrum[sampleIndex]

# Combine successively larger groups using FFT butterflies.
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

# Search positive frequencies only, excluding DC and the mirrored half.
peakIndex = 1
for binIndex in range(2, sampleCount // 2 + 1):
    if abs(spectrum[binIndex]) > abs(spectrum[peakIndex]):
        peakIndex = binIndex
peakFrequency = peakIndex * sampleRate / sampleCount
print('flag{' + str(round(peakFrequency)) + '}')
