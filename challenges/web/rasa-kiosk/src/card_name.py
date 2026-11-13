"""
Compares the printed NAME on two badges without reading it.

The badge name font is too stylized for OCR to read reliably ("IZ" is never
read), so instead of reading the name we compare it visually against the
name on the badge the person registered with:

  1. find the card with ORB + homography and straighten it into the matched
     reference photo's coordinates,
  2. cut out the name area (top of the black panel, above the colored role label),
  3. keep only the white lettering, and compare the two letter shapes with
     normalized cross-correlation (tolerates small shifts and size changes).

Same name on any badge color -> high score; different names -> low score.
"""

import cv2
import numpy as np

from card_detect import detect_cards

ZONE_W, ZONE_H = 400, 200       # name zones are resized to this before comparing
SAME_NAME_THRESHOLD = 0.75      # same name scored 0.95+ in tests, different names <= 0.55
# Name area, as fractions of the black-panel bounding box (stripe excluded)
ZONE_X = (0.30, 0.98)
ZONE_Y = (0.17, 0.55)


def _panel_box(img):
    """Bounding box of the badge's large dark area (card body incl. stripe lettering)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    dark = ((g < 70) * 255).astype(np.uint8)
    k = max(3, int(min(img.shape[:2]) * 0.025)) | 1
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    cnts, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    return cv2.boundingRect(max(cnts, key=cv2.contourArea))


def _cut_above_label(zone):
    """Trim the zone just above the colored role-label box, so only the name remains."""
    hsv = cv2.cvtColor(zone, cv2.COLOR_BGR2HSV)
    vivid = (hsv[..., 1] > 90) & (hsv[..., 2] > 60)
    row_frac = vivid.mean(axis=1)
    h = zone.shape[0]
    start = int(h * 0.35)                       # the label is never in the top third
    rows = np.where(row_frac[start:] > 0.15)[0]
    if len(rows):
        return zone[: start + rows[0]]
    return zone


def rectify(image, scanner):
    """Straighten the single card in `image` into its matched template's frame.

    `scanner` is a CardScanner (reuses its ORB, matcher and templates).
    Returns (straightened BGR image, template's name zone or None), or (None, None)
    if no card is found.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    dets = detect_cards(gray, scanner.templates, scanner.orb, scanner.matcher,
                        scanner.min_matches, scanner.ratio_thresh, w, h, return_h=True)
    if not dets:
        return None, None
    best = dets[0]
    tw, th = best["template_size"]
    return cv2.warpPerspective(image, np.linalg.inv(best["H"]), (tw, th)), best["name_zone"]


def name_zone(image, scanner):
    """The name area of the card in `image`, straightened, or None."""
    flat, fixed = rectify(image, scanner)
    if flat is None:
        return None
    if fixed is not None:
        # Card-cropped template with a known name position (real competition badges:
        # their dark purple stripe defeats the black-panel search below).
        (x0, x1), (y0, y1) = fixed
        fh, fw = flat.shape[:2]
        zone = flat[int(y0 * fh): int(y1 * fh), int(x0 * fw): int(x1 * fw)]
        return cv2.resize(zone, (ZONE_W, ZONE_H), interpolation=cv2.INTER_AREA)
    box = _panel_box(flat)
    if box is None:
        return None
    x, y, w, h = box
    zone = flat[y + int(ZONE_Y[0] * h): y + int(ZONE_Y[1] * h),
                x + int(ZONE_X[0] * w): x + int(ZONE_X[1] * w)]
    if zone.size == 0:
        return None
    zone = _cut_above_label(zone)
    return cv2.resize(zone, (ZONE_W, ZONE_H), interpolation=cv2.INTER_AREA)


def _letters(zone):
    """The name's white lettering as a soft 0-1 mask, cropped tight and resized.

    Only white shapes sitting on the black panel count: the role label's white
    letters sit on a colored box and are dropped. Cropping to the lettering
    makes the comparison independent of where the zone edges landed.
    """
    hsv = cv2.cvtColor(zone, cv2.COLOR_BGR2HSV)
    v, s = hsv[..., 2], hsv[..., 1]
    thresh = max(110.0, float(np.percentile(v, 92)) * 0.65)   # adapts to lighting
    white = ((v > thresh) & (s < 90)).astype(np.uint8)

    zh, zw = white.shape
    n, labels, stats, _ = cv2.connectedComponentsWithStats(white, connectivity=8)
    letters = []                                       # (component mask, height)
    near, far = np.ones((7, 7), np.uint8), np.ones((17, 17), np.uint8)
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 40 or h < 8:
            continue                                   # specks, thin strips
        if area / float(w * h) > 0.85 and w > 3 * h:
            continue                                   # solid wide bar = pale label box, not letters
        if (x <= 1 or x + w >= zw - 1) and h > 0.5 * zh:
            continue                                   # card's white edge
        if w < 10 and h > 3 * w:
            continue                                   # thin sliver of edge / glare
        comp = (labels == i).astype(np.uint8)
        # Background a few px out (past the letter's soft edge) must be black panel;
        # the label's white letters sit on a colored box instead.
        ring = cv2.dilate(comp, far).astype(bool) & ~cv2.dilate(comp, near).astype(bool)
        if ring.any() and np.median(v[ring]) < thresh * 0.6:
            letters.append((comp.astype(bool), h))

    # The name is the big lettering. Much smaller white text that strays into the
    # zone (e.g. the corner "KEEPER OF TOMORROW") would skew the comparison.
    keep = np.zeros_like(white)
    tallest = max((h for _, h in letters), default=0)
    for comp, h in letters:
        if h >= 0.5 * tallest:
            keep[comp] = 1

    ys, xs = np.nonzero(keep)
    if len(ys) < 50:
        return None
    crop = keep[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32)
    crop = cv2.resize(crop, (ZONE_W, ZONE_H), interpolation=cv2.INTER_AREA)
    crop = cv2.copyMakeBorder(crop, 16, 16, 16, 16, cv2.BORDER_CONSTANT, value=0)
    return cv2.GaussianBlur(crop, (7, 7), 0)


def name_similarity(zone_a, zone_b):
    """0-1 similarity of the names in two name zones (from name_zone)."""
    a, b = _letters(zone_a), _letters(zone_b)
    if a is None or b is None:            # no lettering found
        return 0.0
    # Slide the middle of A over B to absorb small misalignments.
    my, mx = int(ZONE_H * 0.08), int(ZONE_W * 0.08)
    core = a[my:-my, mx:-mx]
    score_ab = float(cv2.matchTemplate(b, core, cv2.TM_CCOEFF_NORMED).max())
    core = b[my:-my, mx:-mx]
    score_ba = float(cv2.matchTemplate(a, core, cv2.TM_CCOEFF_NORMED).max())
    return max(0.0, min(score_ab, score_ba))
