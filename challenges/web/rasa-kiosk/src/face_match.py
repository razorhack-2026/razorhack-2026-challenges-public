"""
Live face matching against a stored reference photo (face.jpg).

Loads face.jpg (produced by face_detect.py's focus-lock screenshot, or any photo
with a single clear face in it), extracts its ArcFace embedding once at startup,
then compares every face seen on the webcam against it. When a live face's
embedding is close enough to the reference, prints "Welcome back" to the
terminal and draws a green box; otherwise draws a red box.

This is the natural next step after face_detect.py: same InsightFace model
pack, just with the "recognition" module turned on to get 512-d embeddings
(face.normed_embedding) instead of only bounding boxes.

Install:
    pip install insightface onnxruntime opencv-python numpy
    (GPU users: pip install onnxruntime-gpu instead of onnxruntime)

Usage:
    python face_match.py                     # compares against ./face.jpg
    python face_match.py --reference me.jpg   # use a different reference photo
    python face_match.py --threshold 0.45     # loosen/tighten the match threshold
Press 'q' or ESC to quit.
"""

import argparse
import threading
import time

import cv2
import numpy as np
from insightface.app import FaceAnalysis

RED = (0, 0, 255)     # OpenCV uses BGR
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)

# Cosine similarity of two ArcFace normed embeddings. ~0.5 is a reasonable default
# cutoff for buffalo_l: genuine matches are typically well above it, impostors below.
DEFAULT_THRESHOLD = 0.5

# Don't spam the terminal every frame while the same person stays in view -
# only re-announce a match after this many seconds of continuous matching.
REANNOUNCE_COOLDOWN = 5.0


class ThreadedCamera:
    """Reads frames from the webcam on a background thread.

    A plain cv2.VideoCapture.read() blocks the whole loop until the camera
    driver hands over a frame, which is often the biggest single latency hit
    in a "live" webcam app. Reading on a separate thread means the main loop
    always grabs whatever the newest frame is instead of waiting on I/O -
    detection/recognition runs back-to-back with no idle time in between.
    """

    def __init__(self, src, width, height):
        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera {src}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self._lock = threading.Lock()
        self._frame = None
        self._ok = False
        self._stopped = False

        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()

        # Block briefly until the first real frame arrives so callers don't
        # immediately see (False, None).
        for _ in range(100):
            if self._ok:
                break
            time.sleep(0.01)

    def _update(self):
        while not self._stopped:
            ok, frame = self.cap.read()
            with self._lock:
                self._ok = ok
                self._frame = frame

    def read(self):
        with self._lock:
            if self._frame is None:
                return False, None
            return self._ok, self._frame.copy()

    def release(self):
        self._stopped = True
        self._thread.join(timeout=1.0)
        self.cap.release()


def build_face_matcher(det_size=(320, 320)):
    """Load InsightFace with detection + recognition (embeddings) enabled."""
    app = FaceAnalysis(
        name="buffalo_l",
        allowed_modules=["detection", "recognition"],
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    app.prepare(ctx_id=0, det_size=det_size)
    return app


def load_reference_embedding(app, path):
    """Run the detector+recognizer on a reference photo and return its embedding."""
    ref_img = cv2.imread(path)
    if ref_img is None:
        raise FileNotFoundError(f"Could not read reference image: {path}")

    faces = app.get(ref_img)
    if not faces:
        raise RuntimeError(f"No face found in reference image: {path}")
    if len(faces) > 1:
        print(f"Warning: {len(faces)} faces found in {path}; using the largest one.")
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

    return faces[0].normed_embedding


def cosine_similarity(a, b):
    return float(np.dot(a, b))  # both are already unit-normalized


def main():
    parser = argparse.ArgumentParser(description="Live face matching against a reference photo")
    parser.add_argument("--reference", default="face.jpg", help="Path to the reference face photo")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index")
    parser.add_argument("--min-score", type=float, default=0.5, help="Minimum detection confidence")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="Cosine similarity cutoff to call it a match (0-1)")
    parser.add_argument("--det-size", type=int, default=320, help="Detector input size")
    parser.add_argument("--process-every", type=int, default=2,
                        help="Run detection+matching every Nth frame; reuse results in between")
    parser.add_argument("--width", type=int, default=640, help="Capture width")
    parser.add_argument("--height", type=int, default=480, help="Capture height")
    args = parser.parse_args()

    app = build_face_matcher(det_size=(args.det_size, args.det_size))
    ref_embedding = load_reference_embedding(app, args.reference)
    print(f"Loaded reference face from {args.reference}")

    cap = ThreadedCamera(args.camera, args.width, args.height)

    prev_time = time.time()
    fps = 0.0
    frame_idx = 0

    last_boxes = []      # list of (x1, y1, x2, y2)
    last_sims = []        # matching similarity score per box
    last_matched = []     # bool per box

    last_announced_at = None  # wall-clock time of the last "Welcome back" print

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.005)  # camera thread hasn't produced a frame yet
                continue

            run_detection = (frame_idx % args.process_every == 0)

            if run_detection:
                faces = [f for f in app.get(frame) if f.det_score >= args.min_score]

                boxes, sims, matched = [], [], []
                any_match_this_frame = False
                for f in faces:
                    x1, y1, x2, y2 = f.bbox.astype(int)
                    sim = cosine_similarity(f.normed_embedding, ref_embedding)
                    is_match = sim >= args.threshold
                    boxes.append((x1, y1, x2, y2))
                    sims.append(sim)
                    matched.append(is_match)
                    any_match_this_frame = any_match_this_frame or is_match

                now = time.time()
                if any_match_this_frame:
                    if last_announced_at is None or (now - last_announced_at) >= REANNOUNCE_COOLDOWN:
                        print("Welcome back")
                        last_announced_at = now
                else:
                    last_announced_at = None  # reset so it announces again next time a match starts

                last_boxes, last_sims, last_matched = boxes, sims, matched

            frame_idx += 1

            for box, sim, is_match in zip(last_boxes, last_sims, last_matched):
                x1, y1, x2, y2 = box
                color = GREEN if is_match else RED
                label = f"Welcome back ({sim:.2f})" if is_match else f"No match ({sim:.2f})"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, max(y1 - 8, 15)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            now = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev_time, 1e-6))
            prev_time = now
            cv2.putText(frame, f"Faces: {len(last_boxes)}  FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, WHITE, 2)

            cv2.imshow("Face Match", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()