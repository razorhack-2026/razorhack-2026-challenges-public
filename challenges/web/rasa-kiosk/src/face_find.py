"""
Face scanning with color-coded focus lock, built on InsightFace.

The scanning logic lives in FaceScanner so both this script and the web app
(app.py) can use it:

  - 1 face on screen   -> RED box (eases toward GREEN the longer it's held)
  - 2+ faces on screen -> YELLOW boxes + "Multiple faces on screen"
  - head turned more than --max-yaw degrees -> face is ignored
  - 1 face held steady for FOCUS_SECONDS -> GREEN box, face is captured

When the app is built with recognition enabled, the capture also includes the
face's ArcFace embedding (512-d, unit length). Detection still runs every frame
without recognition, so it stays fast; recognition runs once, at lock time.

Install:
    pip install insightface onnxruntime opencv-python numpy

Run standalone (saves face.jpg on lock):
    python face_find.py
    python face_find.py --camera 1
Press 'r' to reset, 'q' or ESC to quit.
"""

import argparse
import time

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.app.common import Face

RED = (0, 0, 255)      # OpenCV uses BGR
YELLOW = (0, 255, 255)
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)
FOCUS_SECONDS = 3.0     # how long a single face must stay put to be captured
MOVE_TOLERANCE = 0.35   # allowed center-drift (fraction of face width) before timer resets


def build_face_app(det_size=(320, 320), with_recognition=True):
    """Load InsightFace. Recognition is needed to get embeddings for the database."""
    modules = ["detection", "recognition"] if with_recognition else ["detection"]
    app = FaceAnalysis(
        name="buffalo_l",                    # downloads models on first run (~300 MB)
        allowed_modules=modules,
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    app.prepare(ctx_id=0, det_size=det_size)  # ctx_id=-1 forces CPU
    return app


def detect_faces(app, frame, min_score):
    """Detection only - skips recognition so it can run every frame."""
    bboxes, kpss = app.det_model.detect(frame, max_num=0, metric="default")
    faces = []
    for i in range(bboxes.shape[0]):
        score = float(bboxes[i, 4])
        if score < min_score:
            continue
        faces.append(Face(bbox=bboxes[i, 0:4], kps=None if kpss is None else kpss[i], det_score=score))
    return faces


def face_embedding(app, frame, face):
    """Unit-length ArcFace embedding for one detected face, or None if recognition isn't loaded."""
    rec = app.models.get("recognition")
    if rec is None or face.kps is None:
        return None
    emb = np.asarray(rec.get(frame, face), dtype=np.float32).reshape(-1)
    return emb / np.linalg.norm(emb)


def expand_box(x1, y1, x2, y2, pad_ratio, frame_w, frame_h):
    """Grow a bbox outward by pad_ratio on each side, clamped to frame bounds."""
    w, h = x2 - x1, y2 - y1
    px, py = int(w * pad_ratio), int(h * pad_ratio)
    return (max(x1 - px, 0), max(y1 - py, 0), min(x2 + px, frame_w), min(y2 + py, frame_h))


def center_of(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# Generic 3D face model for solvePnP yaw estimation.
# Order matches InsightFace's 5-point kps: left_eye, right_eye, nose, left_mouth, right_mouth.
MODEL_POINTS_3D = np.array([
    (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (0.0, 0.0, 0.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0),
], dtype=np.float64)


def estimate_yaw(kps, frame_w, frame_h):
    """Rough head yaw in degrees (0 = facing camera). Returns None if it fails."""
    image_points = np.asarray(kps, dtype=np.float64)
    focal_length = frame_w
    camera_matrix = np.array([
        [focal_length, 0, frame_w / 2.0],
        [0, focal_length, frame_h / 2.0],
        [0, 0, 1],
    ], dtype=np.float64)
    ok, rotation_vec, _ = cv2.solvePnP(MODEL_POINTS_3D, image_points, camera_matrix,
                                       np.zeros((4, 1)), flags=cv2.SOLVEPNP_EPNP)
    if not ok:
        return None
    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    sy = np.sqrt(rotation_mat[0, 0] ** 2 + rotation_mat[1, 0] ** 2)
    return float(np.degrees(np.arctan2(-rotation_mat[2, 0], sy)))


class FaceScanner:
    """Stateful face scanner: feed it frames, it tracks focus and captures a locked face.

    After a capture, `captured_crop` and `captured_embedding` stay set until reset().
    """

    def __init__(self, app, min_score=0.5, pad=0.3, process_every=2, max_yaw=30.0,
                 focus_seconds=FOCUS_SECONDS):
        self.app = app
        self.min_score = min_score
        self.pad = pad
        self.process_every = process_every
        self.max_yaw = max_yaw
        self.focus_seconds = focus_seconds
        self.reset()

    def reset(self):
        self.frame_idx = 0
        self.last_boxes = []
        self.last_yaws = []
        self.last_color = RED
        self.last_message = ""
        self.focus_start = None
        self.focus_center = None
        self.last_focus_elapsed = None
        self.captured_crop = None
        self.captured_embedding = None

    @property
    def captured(self):
        return self.captured_crop is not None

    def status(self):
        return {
            "count": len(self.last_boxes),
            "message": self.last_message,
            "elapsed": self.last_focus_elapsed,
            "focus_seconds": self.focus_seconds,
            "captured": self.captured,
        }

    def _clear_focus(self):
        self.focus_start = self.focus_center = None
        self.last_focus_elapsed = None

    def _find(self, frame):
        """Faces facing the camera: (padded boxes, yaws, Face objects)."""
        frame_h, frame_w = frame.shape[:2]
        boxes, yaws, kept = [], [], []
        for f in detect_faces(self.app, frame, self.min_score):
            yaw = estimate_yaw(f.kps, frame_w, frame_h) if f.kps is not None else 0.0
            if yaw is not None and abs(yaw) > self.max_yaw:
                continue  # turned too far to the side
            x1, y1, x2, y2 = f.bbox.astype(int)
            boxes.append(expand_box(x1, y1, x2, y2, self.pad, frame_w, frame_h))
            yaws.append(yaw if yaw is not None else 0.0)
            kept.append(f)
        return boxes, yaws, kept

    def capture_still(self, image):
        """Capture from one still image (an uploaded photo) instead of the live feed.

        Same checks as a live scan, minus the hold-still timer.
        Returns None on success, otherwise the reason it was rejected.
        """
        self.reset()
        boxes, _, kept = self._find(image)
        if not boxes:
            return "No face found in that photo. Use one looking straight at the camera."
        if len(boxes) > 1:
            return "That photo has more than one face. Use one with just you."
        x1, y1, x2, y2 = boxes[0]
        crop = image[y1:y2, x1:x2].copy()
        if crop.size == 0:
            return "No face found in that photo. Use one looking straight at the camera."
        self.captured_embedding = face_embedding(self.app, image, kept[0])
        self.captured_crop = crop
        self.last_message = "Face captured"
        return None

    def process(self, frame):
        """Run one step on a BGR frame. Returns an annotated copy for display."""

        if self.frame_idx % self.process_every == 0 and not self.captured:
            boxes, yaws, kept = self._find(frame)
            now = time.time()

            if not boxes:
                self.last_color, self.last_message = RED, "Look straight at the camera"
                self._clear_focus()
            elif len(boxes) > 1:
                self.last_color, self.last_message = YELLOW, "Multiple faces on screen"
                self._clear_focus()
            else:
                box = boxes[0]
                c = center_of(box)
                face_w = box[2] - box[0]
                if self.focus_center is None or np.hypot(c[0] - self.focus_center[0],
                                                         c[1] - self.focus_center[1]) > face_w * MOVE_TOLERANCE:
                    self.focus_start, self.focus_center, elapsed = now, c, 0.0
                else:
                    self.focus_center = c  # follow slow drift
                    elapsed = now - self.focus_start
                self.last_focus_elapsed = elapsed
                self.last_color = lerp_color(RED, GREEN, elapsed / self.focus_seconds)
                self.last_message = "Hold still..."

                if elapsed >= self.focus_seconds:
                    x1, y1, x2, y2 = box
                    crop = frame[y1:y2, x1:x2].copy()
                    if crop.size > 0:
                        self.captured_embedding = face_embedding(self.app, frame, kept[0])
                        self.captured_crop = crop
                        self.last_message = "Face captured"

            self.last_boxes, self.last_yaws = boxes, yaws
        self.frame_idx += 1

        out = frame.copy()
        for (x1, y1, x2, y2), yaw in zip(self.last_boxes, self.last_yaws):
            cv2.rectangle(out, (x1, y1), (x2, y2), self.last_color, 2)
            cv2.putText(out, f"{yaw:+.0f} deg", (x1, max(y1 - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.last_color, 2)
        if self.last_focus_elapsed is not None:
            capped = min(self.last_focus_elapsed, self.focus_seconds)
            cv2.putText(out, f"Focus: {capped:.1f}s / {self.focus_seconds:.1f}s", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.last_color, 2)
        elif self.last_message == "Multiple faces on screen":
            cv2.putText(out, self.last_message, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, YELLOW, 2)
        return out


def main():
    parser = argparse.ArgumentParser(description="Live face detection")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("--pad", type=float, default=0.3)
    parser.add_argument("--det-size", type=int, default=320)
    parser.add_argument("--process-every", type=int, default=2)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--max-yaw", type=float, default=30.0)
    args = parser.parse_args()

    app = build_face_app((args.det_size, args.det_size), with_recognition=False)
    scanner = FaceScanner(app, args.min_score, args.pad, args.process_every, args.max_yaw)

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
                cv2.imwrite("face.jpg", scanner.captured_crop)
                print("Saved focused face to face.jpg")
                written = True
            if scanner.captured:
                cv2.putText(out, "Face locked - saved (r to rescan)", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, GREEN, 2)
            cv2.imshow("Face Detection", out)
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
