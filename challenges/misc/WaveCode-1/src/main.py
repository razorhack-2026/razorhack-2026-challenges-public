# GM-only deterministic waveform builder; Python 3 standard library only.

import csv
import math
from pathlib import Path

challengeRoot = Path(__file__).resolve().parents[1]
sampleRate = 8192
sampleDuration = 2
# Frequency (Hz), amplitude, phase (radians). The strongest tone is unique.
signalTones = ((1373, 0.65, 0.37), (421, 0.18, 1.1), (2387, 0.09, 2.4))
csvPath = challengeRoot / 'dist' / 'beacon.csv'

with csvPath.open('w', newline='') as outputFile:
    csvWriter = csv.writer(outputFile)
    csvWriter.writerow(('timeSeconds', 'amplitude'))
    for sampleIndex in range(sampleRate * sampleDuration):
        sampleTime = sampleIndex / sampleRate
        sampleValue = 0
        for frequency, amplitude, phase in signalTones:
            sampleValue += amplitude * math.sin(2 * math.pi * frequency * sampleTime + phase)
        csvWriter.writerow((f'{sampleTime:.12f}', f'{sampleValue:.12f}'))

print('Generated beacon.csv')
