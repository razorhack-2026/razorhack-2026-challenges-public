"""Turn the public NASA source image into a frame that can't be diffed.

Source: NASA/JPL PIA16613 (NGC 6872, the Condor Galaxy), public domain.
Crops, rescales to 1920x1080 and adds seeded sensor noise, so competitors
can't recover the pre-calibration frame by downloading the original.

    python prep_image.py "PIA16613~orig.jpg" frame.png
"""
import sys

import numpy as np
from PIL import Image

SEED = 1106

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")

# off-centre crop (5000x2812 source), then rescale to 1080p
im = im.crop((310, 120, 4750, 2617)).resize((1920, 1080), Image.LANCZOS)

a = np.asarray(im).astype(np.float32)
rng = np.random.default_rng(SEED)
a += rng.normal(0.0, 2.5, a.shape)
Image.fromarray(np.clip(np.rint(a), 0, 255).astype(np.uint8)).save(out)
print(f"wrote {out}")
