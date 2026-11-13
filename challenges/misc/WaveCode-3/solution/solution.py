# Reference solver. Reads only the three distributed captures.
import argparse
import array
import math
import sys
import wave
from pathlib import Path

import numpy as np

challengeRoot = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(challengeRoot / 'solution'))

from wavecode import (
    bankPilots,
    captureFiles,
    carrierCount,
    carrierDecay,
    carrierFrequency,
    headerBytes,
    loggerGain,
    pilotSamples,
    ringSamples,
    ringStart,
    sampleRate,
    unpackEnvelope,
)


def readCapture(path):
    with wave.open(str(path), 'rb') as inputFile:
        if inputFile.getnchannels() != 1 or inputFile.getsampwidth() != 2:
            raise ValueError(f'{path.name}: unexpected WAV format')
        if inputFile.getframerate() != sampleRate:
            raise ValueError(f'{path.name}: unexpected sample rate')

        frameCount = inputFile.getnframes()

        if frameCount != ringStart + ringSamples:
            raise ValueError(f'{path.name}: unexpected capture length')

        pcm = array.array('h')
        pcm.frombytes(inputFile.readframes(frameCount))

    if sys.byteorder == 'big':
        pcm.byteswap()

    return np.asarray(pcm, dtype=np.float64) / 32767 / loggerGain


def readBankName(samples):
    spectrum = np.abs(np.fft.rfft(samples[:pilotSamples]))
    binWidth = sampleRate / pilotSamples

    return max(bankPilots, key=lambda bank: spectrum[round(bank[1] / binWidth)])[0]


def readFrame(samples):
    segment = samples[ringStart:ringStart + ringSamples]
    sampleTimes = np.arange(ringSamples) / sampleRate

    columns = []
    for symbolIndex in range(carrierCount):
        decay = np.exp(-sampleTimes / carrierDecay(symbolIndex))
        angle = 2 * np.pi * carrierFrequency(symbolIndex) * sampleTimes
        columns.append(decay * np.sin(angle))
        columns.append(decay * np.cos(angle))

    basis = np.stack(columns, axis=1)
    coefficients = np.linalg.lstsq(basis, segment, rcond=None)[0]
    amplitudes = [
        math.hypot(coefficients[2 * symbolIndex], coefficients[2 * symbolIndex + 1])
        for symbolIndex in range(carrierCount)
    ]
    symbols = bytes(
        min(127, max(0, round(amplitude * 128))) for amplitude in amplitudes
    )

    if symbols[:len(headerBytes)] != headerBytes:
        raise ValueError('Frame header did not decode; check the ring-down window')

    return symbols[len(headerBytes):]


def main():
    argumentParser = argparse.ArgumentParser(
        description='Decode the three Certus Quartz logger captures.',
    )
    argumentParser.add_argument(
        'capturePaths', nargs='*', type=Path,
        help='One WAV per bank, in any order.',
    )
    arguments = argumentParser.parse_args()
    capturePaths = arguments.capturePaths or [
        challengeRoot / 'dist' / fileName for fileName in captureFiles
    ]

    if len(capturePaths) != len(bankPilots):
        raise SystemExit('Supply exactly three captures')

    payloads = {}

    for path in capturePaths:
        samples = readCapture(path)
        bankName = readBankName(samples)

        if bankName in payloads:
            raise SystemExit(f'Two captures claim bank {bankName}')

        payloads[bankName] = readFrame(samples)

    envelope = b''.join(payloads[bankName] for bankName, _ in bankPilots)
    print(unpackEnvelope(envelope).decode('ascii'))


if __name__ == '__main__':
    main()
