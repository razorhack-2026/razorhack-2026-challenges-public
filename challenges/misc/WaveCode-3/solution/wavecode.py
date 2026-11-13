# GM-only shared constants and payload helpers for WaveCode 3.
import math
import zlib


sampleRate = 48000
loggerGain = 0.04

carrierCount = 25
headerBytes = b'WC2:0010:'
payloadBytes = 16
envelopeBytes = 48
messageLimit = 42
qualityFactor = 300

pilotSamples = 9600
driveGapSamples = 1440
driveSamples = 7200
ringGapSamples = 960
ringSamples = 72000
ringStart = pilotSamples + driveGapSamples + driveSamples + ringGapSamples

pilotAmplitude = 0.5
driveAmplitude = 0.6
driveStart = 200
driveEnd = 2000

bankPilots = (('A', 130), ('B', 150), ('C', 170))

# Filenames are opaque identifiers. They deliberately do not match bank order.
captureFiles = (
    '0e4b0ee53f0640ce.wav',
    '10516b7a7ff9b204.wav',
    'd71b1d23309a0b2e.wav',
)
captureBanks = (1, 2, 0)


def carrierFrequency(symbolIndex):
    return 8 + 4 * symbolIndex


def carrierDecay(symbolIndex):
    return qualityFactor / (math.pi * carrierFrequency(symbolIndex))


def packEnvelope(packetBytes):
    if not 0 < len(packetBytes) <= messageLimit:
        raise ValueError(f'Message must contain between 1 and {messageLimit} bytes')

    checksum = zlib.crc32(packetBytes)
    digits = bytes((checksum >> shift) & 0x7F for shift in (28, 21, 14, 7, 0))

    return (
        bytes((len(packetBytes),))
        + packetBytes
        + bytes(messageLimit - len(packetBytes))
        + digits
    )


def unpackEnvelope(envelope):
    if len(envelope) != envelopeBytes:
        raise ValueError(f'Payload must contain {envelopeBytes} symbols')

    length = envelope[0]

    if not 1 <= length <= messageLimit:
        raise ValueError('Invalid message length')

    packetBytes = bytes(envelope[1:1 + length])

    if any(envelope[1 + length:messageLimit + 1]):
        raise ValueError('Padding is not zero')

    checksum = 0
    for digit in envelope[messageLimit + 1:envelopeBytes]:
        checksum = (checksum << 7) | digit

    if checksum != zlib.crc32(packetBytes):
        raise ValueError('Checksum mismatch')

    return packetBytes
