"""
Card detection for the three RASA badge types (Player, Sponsor, GM).

The scanning logic lives in CardScanner so both this script and the web app
(app.py) can use it:

  - 1 card on screen  -> RED box (eases toward GREEN the longer it's held)
  - 2+ cards on screen -> YELLOW boxes + "Multiple cards on screen"
  - 1 card held steady for FOCUS_SECONDS -> GREEN box, card is captured

HOW A CARD IS FOUND: ORB keypoint matching + homography against one reference
photo per card type (no training needed). See the notes at the bottom of this
docstring for when to switch to a trained detector.

HOW THE CARD TYPE IS DECIDED: by the color of the badge's side stripe, not by
which template matched. All three badges share the same layout, logo and text,
so ORB can't reliably tell them apart - but the stripe color can (red = Player,
green = Sponsor, purple = GM). This is also the "proper color" check the
elevation challenge needs.

Run standalone (saves card.jpg on lock):
    python card_detect.py
    python card_detect.py --templates-dir mycards --min-matches 10
Press 'r' to reset, 'q' or ESC to quit.

If you later collect many photos per card type, a small trained detector
(e.g. YOLOv8n) can replace detect_cards() and everything else stays the same.
"""

import argparse
import os
import time

import cv2
import numpy as np

RED = (0, 0, 255)      # OpenCV uses BGR
YELLOW = (0, 255, 255)
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)

FOCUS_SECONDS = 4.0     # how long a single card must stay put to be captured
MOVE_TOLERANCE = 0.35   # allowed center-drift (fraction of box width) before timer resets
NMS_IOU_THRESH = 0.3    # overlapping detections above this are the same physical card

# (display label, filename in --templates-dir[, name zone])
# The optional name zone is where the printed name sits, as ((x0, x1), (y0, y1))
# fractions of the template image - only valid when the template is cropped
# tightly to the card. Without one, card_name.py falls back to finding the
# black panel (works for the prototype badges, not the real competition ones).
REAL_CARD_NAME_ZONE = ((0.34, 0.97), (0.22, 0.37))
DEFAULT_TEMPLATES = [
    ("Sponsor Card", "Sponsor_Card1.jpeg"),
    ("Player Card", "Player_Card1.jpeg"),
    ("GM Card", "GM_Card_real.jpeg", REAL_CARD_NAME_ZONE),
]

# Stripe colors as OpenCV hue ranges (0-179). The tan desk sits around 10-30,
# deliberately outside all of these.
CARD_COLOR_HUES = {
    "red":    [(0, 10), (170, 180)],
    "green":  [(40, 95)],
    "purple": [(110, 160)],
}
MIN_SATURATION = 90
MIN_VALUE = 60


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def center_of(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def iou(box_a, box_b):
    xa, ya = max(box_a[0], box_b[0]), max(box_a[1], box_b[1])
    xb, yb = min(box_a[2], box_b[2]), min(box_a[3], box_b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def classify_card_color(crop_bgr):
    """Return (color_name, confidence 0-1) for a card crop, or (None, 0.0) if unsure.

    Counts strongly-colored pixels in each hue range and picks the dominant one.
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return None, 0.0
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    vivid = (s > MIN_SATURATION) & (v > MIN_VALUE)

    counts = {}
    for name, ranges in CARD_COLOR_HUES.items():
        mask = np.zeros_like(vivid)
        for lo, hi in ranges:
            mask |= (h >= lo) & (h < hi)
        counts[name] = int((mask & vivid).sum())

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    (best, best_n), (_, second_n) = ranked[0], ranked[1]
    total = crop_bgr.shape[0] * crop_bgr.shape[1]
    # Need a visible stripe (>= 2% of the crop) that clearly beats the runner-up.
    if best_n < 0.02 * total or best_n < 2 * second_n:
        return None, 0.0
    return best, best_n / max(best_n + second_n, 1)


def load_templates(templates_dir, orb, template_list=DEFAULT_TEMPLATES):
    """Read each reference card image and precompute its ORB keypoints/descriptors."""
    templates = []
    for label, filename, *name_zone in template_list:
        path = os.path.join(templates_dir, filename)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"Warning: could not read template '{path}', skipping.")
            continue
        kp, des = orb.detectAndCompute(img, None)
        if des is None or len(kp) < 10:
            print(f"Warning: too few features found in '{path}', skipping.")
            continue
        h, w = img.shape
        corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
        templates.append({"label": label, "kp": kp, "des": des, "corners": corners, "size": (w, h),
                          "name_zone": name_zone[0] if name_zone else None})
        print(f"Loaded template '{label}' from {path} ({len(kp)} features)")
    if not templates:
        raise RuntimeError(f"No usable templates found in '{templates_dir}'.")
    return templates


def detect_cards(gray_frame, templates, orb, matcher, min_matches, ratio_thresh, frame_w, frame_h,
                 return_h=False):
    """Match every template against the frame. Returns [{"label", "box", "quad", "score"}].

    With return_h=True each detection also carries "H" (template -> frame homography)
    and "template_size" (w, h), used to straighten the card, plus the template's "name_zone".
    """
    kp_frame, des_frame = orb.detectAndCompute(gray_frame, None)
    if des_frame is None or len(kp_frame) < 2:
        return []

    detections = []
    for tmpl in templates:
        matches = matcher.knnMatch(tmpl["des"], des_frame, k=2)
        good = [p[0] for p in matches if len(p) == 2 and p[0].distance < ratio_thresh * p[1].distance]
        if len(good) < min_matches:
            continue

        src_pts = np.float32([tmpl["kp"][m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if H is None:
            continue
        inliers = int(mask.sum()) if mask is not None else len(good)
        if inliers < min_matches:
            continue

        quad = cv2.perspectiveTransform(tmpl["corners"], H)
        xs, ys = quad[:, 0, 0], quad[:, 0, 1]
        x1, y1 = int(max(xs.min(), 0)), int(max(ys.min(), 0))
        x2, y2 = int(min(xs.max(), frame_w)), int(min(ys.max(), frame_h))
        if x2 <= x1 or y2 <= y1:
            continue
        det = {"label": tmpl["label"], "box": (x1, y1, x2, y2), "quad": quad, "score": inliers}
        if return_h:
            det.update(H=H, template_size=tmpl["size"], name_zone=tmpl["name_zone"])
        detections.append(det)

    # The same physical card can match several templates (shared layout) - keep the best per overlap.
    detections.sort(key=lambda d: d["score"], reverse=True)
    kept = []
    for d in detections:
        if all(iou(d["box"], k["box"]) < NMS_IOU_THRESH for k in kept):
            kept.append(d)
    return kept


class CardScanner:
    """Stateful card scanner: feed it frames, it tracks focus and captures a locked card.

    After a capture, `captured_crop` / `captured_color` stay set until reset().
    """

    def __init__(self, templates_dir="card_templates", min_matches=15, ratio_thresh=0.75,
                 nfeatures=1000, process_every=2, focus_seconds=FOCUS_SECONDS, templates=None):
        self.orb = cv2.ORB_create(nfeatures=nfeatures)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        # Pass `templates` to share already-loaded ones; the ORB and matcher stay per-scanner.
        self.templates = load_templates(templates_dir, self.orb) if templates is None else templates
        self.min_matches = min_matches
        self.ratio_thresh = ratio_thresh
        self.process_every = process_every
        self.focus_seconds = focus_seconds
        self.reset()

    def reset(self):
        self.frame_idx = 0
        self.last_detections = []
        self.last_colors = []
        self.last_color = RED
        self.last_message = ""
        self.focus_start = None
        self.focus_center = None
        self.last_focus_elapsed = None
        self.captured_crop = None
        self.captured_color = None

    @property
    def captured(self):
        return self.captured_crop is not None

    def status(self):
        return {
            "count": len(self.last_detections),
            "message": self.last_message,
            "elapsed": self.last_focus_elapsed,
            "focus_seconds": self.focus_seconds,
            "captured": self.captured,
            "color": self.captured_color if self.captured else
                     (self.last_colors[0] if len(self.last_colors) == 1 else None),
        }

    def _clear_focus(self):
        self.focus_start = self.focus_center = None
        self.last_focus_elapsed = None

    def _find(self, frame):
        """Cards in the frame and each one's stripe color: (detections, colors)."""
        frame_h, frame_w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = detect_cards(gray, self.templates, self.orb, self.matcher,
                                  self.min_matches, self.ratio_thresh, frame_w, frame_h)
        colors = []
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            colors.append(classify_card_color(frame[y1:y2, x1:x2])[0])
        return detections, colors

    def capture_still(self, image):
        """Capture from one still image (an uploaded photo) instead of the live feed.

        Same checks as a live scan, minus the hold-still timer.
        Returns None on success, otherwise the reason it was rejected.
        """
        self.reset()
        detections, colors = self._find(image)
        if not detections:
            return "No badge found in that photo. Use a clear, flat, well-lit shot of the front."
        if len(detections) > 1:
            return "That photo has more than one badge. Use one with just your badge."
        x1, y1, x2, y2 = detections[0]["box"]
        crop = image[y1:y2, x1:x2].copy()
        if crop.size == 0:
            return "No badge found in that photo. Use a clear, flat, well-lit shot of the front."
        self.last_detections, self.last_colors = detections, colors
        self.captured_crop = crop
        self.captured_color = colors[0]
        self.last_message = "Card captured"
        return None

    def process(self, frame):
        """Run one step on a BGR frame. Returns an annotated copy for display."""

        if self.frame_idx % self.process_every == 0 and not self.captured:
            detections, colors = self._find(frame)
            now = time.time()

            if not detections:
                self.last_color, self.last_message = RED, "Hold your card up to the camera"
                self._clear_focus()
            elif len(detections) > 1:
                self.last_color, self.last_message = YELLOW, "Multiple cards on screen"
                self._clear_focus()
            else:
                box = detections[0]["box"]
                c = center_of(box)
                box_w = box[2] - box[0]
                if self.focus_center is None or np.hypot(c[0] - self.focus_center[0],
                                                         c[1] - self.focus_center[1]) > box_w * MOVE_TOLERANCE:
                    self.focus_start, self.focus_center, elapsed = now, c, 0.0
                else:
                    self.focus_center = c
                    elapsed = now - self.focus_start
                self.last_focus_elapsed = elapsed
                self.last_color = lerp_color(RED, GREEN, elapsed / self.focus_seconds)
                self.last_message = "Hold still..."

                if elapsed >= self.focus_seconds:
                    x1, y1, x2, y2 = box
                    crop = frame[y1:y2, x1:x2].copy()
                    if crop.size > 0:
                        self.captured_crop = crop
                        self.captured_color = colors[0]
                        self.last_message = "Card captured"

            self.last_detections, self.last_colors = detections, colors
        self.frame_idx += 1

        out = frame.copy()
        for det, color_name in zip(self.last_detections, self.last_colors):
            x1, y1, x2, y2 = det["box"]
            cv2.rectangle(out, (x1, y1), (x2, y2), self.last_color, 2)
            tag = f"{color_name} card" if color_name else "card (color?)"
            cv2.putText(out, tag, (x1, max(y1 - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.last_color, 2)
        if self.last_focus_elapsed is not None:
            capped = min(self.last_focus_elapsed, self.focus_seconds)
            cv2.putText(out, f"Focus: {capped:.1f}s / {self.focus_seconds:.1f}s", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.last_color, 2)
        elif self.last_message == "Multiple cards on screen":
            cv2.putText(out, self.last_message, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, YELLOW, 2)
        return out


def main():
    parser = argparse.ArgumentParser(description="Live card detection (ORB feature matching)")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--templates-dir", default="card_templates")
    parser.add_argument("--min-matches", type=int, default=15)
    parser.add_argument("--ratio-thresh", type=float, default=0.75)
    parser.add_argument("--nfeatures", type=int, default=1000)
    parser.add_argument("--process-every", type=int, default=2)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()

    scanner = CardScanner(args.templates_dir, args.min_matches, args.ratio_thresh,
                          args.nfeatures, args.process_every)
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera {args.camera}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    written = False
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to read frame from camera.")
                break
            out = scanner.process(frame)
            if scanner.captured and not written:
                cv2.imwrite("card.jpg", scanner.captured_crop)
                print(f"Saved {scanner.captured_color or 'unknown-color'} card to card.jpg")
                written = True
            if scanner.captured:
                cv2.putText(out, "Card locked - saved (r to rescan)", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, GREEN, 2)
            cv2.imshow("Card Detection", out)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("r"):
                scanner.reset()
                written = False
                print("Reset to initial state.")
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
