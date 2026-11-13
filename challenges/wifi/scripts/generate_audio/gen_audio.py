import freetype
import numpy as np
from scipy.io import wavfile
from PIL import Image

""" Text used to generate Heimdall's riddle (capture-02.wav):
If you want my password, you must answer my riddle.
.
Two brothers sleep within the stone.
The first is red and ruh-ged, for-jing the swords of empires and the blood in your vaynes.

The second is bright and tyme-less, cov-eh-ted by crao-ns, never tarnished by heh-vee raynes.

Speak their ch-rue names, bound together as one.
"""

SR = 44100

# Image/audio encoding settings
FMIN, FMAX = 400, 1650
IMG_H = 40
COL_MS = 40
COL_SAMPLES = int(SR * COL_MS / 1000)

# Noise
NOISE_STRENGTH = 0.8

# Dial-up settings
DIALUP_SECONDS = 3.0
DIALUP_BEGINNING_GAP = 1.0
DIALUP_RANGE = [750, 1000, 1250, 1500, 1750, 2000]

BLOCK_GAP = 1
MESSAGE_GAIN = 4.0

# Text
TEXT_MESSAGE = ""
CODE = "OVERRIDE: ODN-CLOS-EYES"

WINGDING_FONT = "./fonts/wingding.ttf"
TEXT_FONT = "./fonts/DejaVuSansMono.ttf"


def render_message_mask(font_path, message, img_h):
    """Render text into a boolean pixel mask."""

    face = freetype.Face(font_path)

    try:
        face.select_charmap(freetype.FT_ENCODING_MS_SYMBOL)
        is_symbol_font = True
    except freetype.FT_Exception:
        face.select_charmap(freetype.FT_ENCODING_UNICODE)
        is_symbol_font = False

    face.set_pixel_sizes(0, int(img_h * 0.8))

    pen_x = 0
    max_ascender = 0
    max_descender = 0

    glyphs = []

    for ch in message:
        code = (0xF000 + ord(ch)) if is_symbol_font else ord(ch)

        face.load_char(code, freetype.FT_LOAD_RENDER)

        slot = face.glyph
        bmp = slot.bitmap

        buf = (
            np.array(
                bmp.buffer,
                dtype=np.uint8
            ).reshape(
                bmp.rows,
                bmp.width
            ).copy()
            if bmp.rows and bmp.width
            else None
        )

        glyphs.append((
            pen_x + slot.bitmap_left,
            slot.bitmap_top,
            buf
        ))

        pen_x += slot.advance.x >> 6

        max_ascender = max(
            max_ascender,
            slot.bitmap_top
        )

        max_descender = max(
            max_descender,
            (bmp.rows - slot.bitmap_top)
            if bmp.rows
            else 0
        )

    width = max(
        1,
        pen_x
    ) + 2 * BLOCK_GAP

    height = max(
        1,
        max_ascender + max_descender + 10
    )

    canvas = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    for x0, top, buf in glyphs:
        if buf is None:
            continue

        y0 = max_ascender - top + 5

        h, w = buf.shape

        canvas[
            y0:y0 + h,
            x0 + BLOCK_GAP:
            x0 + BLOCK_GAP + w
        ] = np.maximum(
            canvas[
                y0:y0 + h,
                x0 + BLOCK_GAP:
                x0 + BLOCK_GAP + w
            ],
            buf
        )

    img = Image.fromarray(canvas).resize(
        (width, img_h)
    )

    return np.array(img) > 40


def image_to_audio(pixels):
    """Convert a text pixel mask into frequency-over-time audio."""

    img_w = pixels.shape[1]

    n_samples = img_w * COL_SAMPLES

    result = np.zeros(n_samples)

    # Top of image = high frequency
    # Bottom of image = low frequency
    freqs = np.linspace(
        FMAX,
        FMIN,
        IMG_H
    )

    window = np.hanning(COL_SAMPLES)

    t_col = np.arange(
        COL_SAMPLES
    ) / SR

    for col in range(img_w):

        on_rows = np.where(
            pixels[:, col]
        )[0]

        if len(on_rows) == 0:
            continue

        seg = np.zeros(
            COL_SAMPLES
        )

        for row in on_rows:
            seg += np.sin(
                2 * np.pi *
                freqs[row] *
                t_col
            )

        start = col * COL_SAMPLES

        result[
            start:start + COL_SAMPLES
        ] += seg * window

    return result


# ============================================================
# Render both text sections
# ============================================================

handshake_pixels = render_message_mask(
    TEXT_FONT,
    TEXT_MESSAGE,
    IMG_H
)

message_pixels = render_message_mask(
    WINGDING_FONT,
    CODE,
    IMG_H
)


# ============================================================
# Convert both text sections to audio
# ============================================================

handshake_audio = image_to_audio(
    handshake_pixels
)

message_audio = image_to_audio(
    message_pixels
)


# ============================================================
# Start with the main message waveform
# ============================================================

audio = message_audio


# ============================================================
# Generate dial-up handshake
# ============================================================

if DIALUP_SECONDS > 0:

    rng = np.random.default_rng()

    bit_samples = max(
        1,
        int(SR * 0.01)
    )

    bit_count = int(
        DIALUP_SECONDS *
        SR /
        bit_samples
    )

    bits = rng.integers(
        0,
        len(DIALUP_RANGE),
        size=bit_count
    )

    bit_t = np.arange(
        bit_samples
    ) / SR

    bit_window = np.hanning(
        bit_samples
    )

    dialup = np.concatenate([
        np.sin(
            2 * np.pi *
            DIALUP_RANGE[bit] *
            bit_t
        ) * bit_window

        for bit in bits
    ]) * MESSAGE_GAIN


    # ========================================================
    # Initial silence
    # ========================================================

    if DIALUP_BEGINNING_GAP > 0:

        beginning_gap = np.zeros(
            int(
                SR *
                DIALUP_BEGINNING_GAP
            )
        )

        dialup = np.concatenate((
            beginning_gap,
            dialup
        ))


    # ========================================================
    # Gaps between sections
    # ========================================================

    section_gap = np.zeros(
        int(
            SR *
            BLOCK_GAP
        )
    )


    # ========================================================
    # Combine:
    #
    # silence
    #     ↓
    # dial-up
    #     ↓
    # handshake text
    #     ↓
    # gap
    #     ↓
    # main message
    # ========================================================

    audio = np.concatenate([
        dialup,

        section_gap,

        handshake_audio * MESSAGE_GAIN,

        section_gap,

        message_audio * MESSAGE_GAIN
    ])


# ============================================================
# Add broadband noise
# ============================================================

if NOISE_STRENGTH > 0:

    audio += np.random.normal(
        0.0,
        NOISE_STRENGTH,
        size=audio.shape
    )

# ============================================================
# Normalize and write WAV
# ============================================================

audio = (
    audio /
    (np.max(np.abs(audio)) + 1e-9)
    * 0.8
)

wavfile.write(
    "capture-01.wav",
    SR,
    (audio * 32767).astype(np.int16)
)

print("Generated .wav")
print(f"Text Message: {TEXT_MESSAGE}")
print(f"Code:   {CODE}")