# GM-only builder. Python 3 standard library only.
import csv
import math
from pathlib import Path

challengeRoot = Path(__file__).resolve().parents[1]
packetText = (challengeRoot / 'src' / 'packet.txt').read_text(encoding='ascii')
packetBytes = packetText.encode('ascii')
frameText = f'WC2:{len(packetBytes):04X}:' + packetText
sampleRate = 4096
sampleCount = 4096
firstFrequency = 8
frequencyStep = 4
assert len(packetBytes) <= 65535
assert firstFrequency + frequencyStep * (len(frameText) - 1) < sampleRate / 2

with (challengeRoot / 'dist' / 'beacon.csv').open('w', newline='') as outputFile:
    csvWriter = csv.writer(outputFile)
    csvWriter.writerow(('timeSeconds', 'amplitude'))
    for sampleIndex in range(sampleCount):
        sampleTime = sampleIndex / sampleRate
        sampleValue = 0
        for symbolIndex, symbolValue in enumerate(frameText.encode('ascii')):
            frequency = firstFrequency + frequencyStep * symbolIndex
            sampleValue += symbolValue / 128 * math.sin(2 * math.pi * frequency * sampleTime)
        csvWriter.writerow((f'{sampleTime:.12f}', f'{sampleValue:.12f}'))
print('Generated beacon.csv')
