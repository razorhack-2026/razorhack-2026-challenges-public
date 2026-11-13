# GM-only builder. Writes three logger captures; the packet never appears in them.
import array
import math
import sys
import wave
from pathlib import Path

challengeRoot = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(challengeRoot / 'solution'))

from wavecode import (
    bankPilots,
    captureBanks,
    captureFiles,
    carrierCount,
    carrierDecay,
    carrierFrequency,
    driveAmplitude,
    driveEnd,
    driveGapSamples,
    driveSamples,
    driveStart,
    envelopeBytes,
    headerBytes,
    loggerGain,
    packEnvelope,
    payloadBytes,
    pilotAmplitude,
    pilotSamples,
    ringGapSamples,
    ringSamples,
    ringStart,
    sampleRate,
)


packetText = (challengeRoot / 'src' / 'packet.txt').read_text(encoding='ascii').rstrip('\n')
packetBytes = packetText.encode('ascii')

assert all(symbolValue < 128 for symbolValue in packetBytes)

envelope = packEnvelope(packetBytes)
frames = [
    headerBytes + envelope[offset:offset + payloadBytes]
    for offset in range(0, envelopeBytes, payloadBytes)
]

assert len(frames) == len(bankPilots)
assert all(len(frame) == carrierCount for frame in frames)


def pilotValues(frequency):
    return [
        pilotAmplitude * math.sin(2 * math.pi * frequency * sampleIndex / sampleRate)
        for sampleIndex in range(pilotSamples)
    ]


def driveValues():
    values = []
    phase = 0
    for sampleIndex in range(driveSamples):
        fraction = sampleIndex / (driveSamples - 1)
        frequency = driveStart + (driveEnd - driveStart) * fraction
        phase += 2 * math.pi * frequency / sampleRate
        values.append(driveAmplitude * math.sin(phase))
    return values


def ringDownValues(frameBytes):
    values = []
    for sampleIndex in range(ringSamples):
        sampleTime = sampleIndex / sampleRate
        sampleValue = 0
        for symbolIndex, symbolValue in enumerate(frameBytes):
            decay = math.exp(-sampleTime / carrierDecay(symbolIndex))
            angle = 2 * math.pi * carrierFrequency(symbolIndex) * sampleTime
            sampleValue += symbolValue / 128 * decay * math.sin(angle)
        values.append(sampleValue)
    return values


def writeCapture(path, bankName, pilotFrequency, frameBytes):
    values = []
    values += pilotValues(pilotFrequency)
    values += [0.0] * driveGapSamples
    values += driveValues()
    values += [0.0] * ringGapSamples
    values += ringDownValues(frameBytes)

    assert len(values) == ringStart + ringSamples

    recorded = [value * loggerGain for value in values]

    if max(abs(value) for value in recorded) > 0.95:
        raise ValueError('Capture would clip at the published logger gain')

    pcm = array.array('h', (round(value * 32767) for value in recorded))

    if sys.byteorder == 'big':
        pcm.byteswap()

    with wave.open(str(path), 'wb') as outputFile:
        outputFile.setnchannels(1)
        outputFile.setsampwidth(2)
        outputFile.setframerate(sampleRate)
        outputFile.writeframes(pcm.tobytes())

    print(f'Generated {path.name} (bank {bankName})')


for fileIndex, bankIndex in enumerate(captureBanks):
    bankName, pilotFrequency = bankPilots[bankIndex]
    outputPath = challengeRoot / 'dist' / captureFiles[fileIndex]
    writeCapture(outputPath, bankName, pilotFrequency, frames[bankIndex])
