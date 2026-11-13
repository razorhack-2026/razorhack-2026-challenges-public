"""
Reads the printed text on a captured badge (OCR) and finds its role label.

Uses RapidOCR (ONNX models bundled in the pip package, runs on the same
onnxruntime as InsightFace - no extra downloads, ~0.5 s per card on CPU).

Role labels (FLIGHT CREW / SPONSER / GAMEMASTER) are printed in a plain bold
font and read reliably. Names are printed in a blocky display font that OCR
often misreads or misses, so a name can only be spot-checked (see name_conflict):
OCR tends to catch part of a name, or none of it.
"""

import re
import threading

import cv2

MIN_OCR_WIDTH = 500   # upscale small crops to at least this width before OCR
# Printed on every badge, so never part of the holder's name.
FIXED_TEXT = ("KEEPER", "TOMORROW", "ACCESS", "AREAS", "RESTRICTED", "LIMITED", "RAZORPOWER", "CYBERHOGS")
BADGE_WORD = re.compile(r"RA[A-Z]{0,2}|ALL")   # fragments of the sideways RASA logo; ALL ACCESS


def normalize(text):
    """Uppercase letters only: 'Flight crew!' -> 'FLIGHTCREW'."""
    return re.sub(r"[^A-Z]", "", text.upper())


def _contains_fuzzy(haystack, needle, max_mismatch=1):
    """True if needle appears in haystack with at most `max_mismatch` wrong letters."""
    n = len(needle)
    for i in range(len(haystack) - n + 1):
        window = haystack[i:i + n]
        if sum(a != b for a, b in zip(window, needle)) <= max_mismatch:
            return True
    return False


def name_fragments(texts, labels):
    """The OCR fragments that could be the holder's name: everything but the badge's
    fixed text, role labels, logo, placeholder Xs and "(title)" lines."""
    fragments = []
    for text in texts:
        word = normalize(text)
        if (len(word) < 3 or "(" in text or BADGE_WORD.fullmatch(word) or set(word) == {"X"}
                or any(fixed in word for fixed in FIXED_TEXT)
                or any(_contains_fuzzy(word, normalize(label)) for label in labels.values())):
            continue
        fragments.append(text)
    return fragments


def _fits(haystack, needle):
    """Fuzzy contains, exact for short words: one wrong letter in "ONE" would fit too much."""
    return _contains_fuzzy(haystack, needle, max_mismatch=1 if len(needle) >= 5 else 0)


def name_conflict(typed, texts, labels):
    """What the badge reads, if that clearly isn't `typed`; otherwise None.

    Only rejects when OCR found name text and none of it fits, because OCR often
    catches part of a name (PLAYER ONE -> "ONE") or none of it.
    """
    want = normalize(typed)
    fragments = name_fragments(texts, labels)
    if not want or not fragments:
        return None
    for text in fragments:
        word = normalize(text)
        if _fits(want, word) or _fits(word, want):
            return None
    return " ".join(fragments)


# Handwritten badges (late registrations, name filled in with a paint marker).
# Printed names are uppercase and at most ~2.3x the role label's height; marker
# lettering came out ~3x and mixed case. Lenient on purpose: a false positive only
# skips the name check, which the event is fine with.
HANDWRITTEN_HEIGHT_RATIO = 2.5    # name line this many times the label height -> handwritten
HANDWRITTEN_LOWER_RATIO = 1.6     # lowercase name text at least this tall -> handwritten
HANDWRITTEN_LINES = 3             # printed badges carry at most a name and a title line
HANDWRITTEN_LINE_RATIO = 1.4      # ...so this many lines at least this tall -> handwritten


def _box_size(quad):
    """(width, height) of an OCR box quad [[x, y] x4], tolerant of slight rotation."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad
    w = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    h = ((x3 - x0) ** 2 + (y3 - y0) ** 2) ** 0.5
    return w, h


def looks_handwritten(boxes, labels):
    """True if the badge's name looks hand-filled rather than printed.

    `boxes` is [(text, width, height)] from CardReader.read_boxes. Compares the name
    lettering against the printed role label on the same badge, so it doesn't
    depend on photo scale.
    """
    label_words = [normalize(l) for l in labels.values()]
    label_h = [h for t, w, h in boxes if any(_contains_fuzzy(normalize(t), l) for l in label_words)]
    # Only horizontal lines: the sideways RASA logo reads as a huge tall fragment.
    names = [(t, h) for t, w, h in boxes if w > h and name_fragments([t], labels)]
    if not label_h:
        return False
    ref = max(label_h)
    # Count only lines clearly bigger than the label: OCR clips fixed badge text on
    # tilted shots ("KEEPE", "CYBERHOG"), and that text is label-sized.
    if sum(h >= HANDWRITTEN_LINE_RATIO * ref for _, h in names) >= HANDWRITTEN_LINES:
        return True
    for text, h in names:
        if h >= HANDWRITTEN_HEIGHT_RATIO * ref:
            return True
        if re.search(r"[a-z]", text) and h >= HANDWRITTEN_LOWER_RATIO * ref:
            return True
    return False


class CardReader:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR  # imported here so other modules don't need it
        self.ocr = RapidOCR()
        self._lock = threading.Lock()   # one reader serves every player's kiosk

    def read_boxes(self, crop_bgr):
        """All text fragments OCR finds on the card, in reading order, as (text, width, height)."""
        if crop_bgr is None or crop_bgr.size == 0:
            return []
        h, w = crop_bgr.shape[:2]
        if w < MIN_OCR_WIDTH:
            scale = MIN_OCR_WIDTH / w
            crop_bgr = cv2.resize(crop_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        with self._lock:
            result, _ = self.ocr(crop_bgr)
        return [(r[1], *_box_size(r[0])) for r in (result or [])]

    def read_text(self, crop_bgr):
        """All text fragments OCR finds on the card, in reading order."""
        return [t for t, _, _ in self.read_boxes(crop_bgr)]

    def find_label(self, crop_bgr, labels):
        """Which of `labels` ({key: printed label}) appears on the card.

        Returns (key or None, raw_text_list, handwritten). If more than one label
        is found, key is None - a card shouldn't carry two roles. `handwritten` is
        True when the name looks hand-filled (see looks_handwritten).
        """
        boxes = self.read_boxes(crop_bgr)
        texts = [t for t, _, _ in boxes]
        joined = "".join(normalize(t) for t in texts)
        found = [key for key, label in labels.items() if _contains_fuzzy(joined, normalize(label))]
        return (found[0] if len(found) == 1 else None), texts, looks_handwritten(boxes, labels)
