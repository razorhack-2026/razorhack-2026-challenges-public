"""
Razorhack kiosk: a local website for checking competitors in and logging them
into two demo applications.

  Add New User  - scan face -> confirm -> scan card -> confirm -> enter name -> saved
  General       - face must match a registered user, then that user's badge
  Admin         - same, but only users registered as GM or Sponsor get in
  Update Info   - scan face (finds who they are), then scan the current badge,
                  then the new badge (may be a different level) -> confirm -> saved

The camera is the player's own: the page opens it in the browser and POSTs frames
here (browsers only allow that on HTTPS or localhost). Any face or badge scan can
instead use an uploaded photo; it goes through the same checks (one face facing the
camera / one badge, then the step's usual checks). Each browser session gets its own
Kiosk, so players on the hosted site don't share a scan or login.

A successful login prints a success message in the terminal and opens that
level's document library (templates/general_documents or admin_documents) for
ACCESS_SECONDS. An Admin login opens the General library too.

A badge is "theirs" when:
  - its stripe color and printed role label agree (red + FLIGHT CREW,
    green + SPONSER, purple + GAMEMASTER) - read by color check + OCR,
  - its level matches the level they're registered at, and
  - the name printed on it matches the name on their registered badge -
    compared visually (see card_name.py), since the name font defeats OCR.

Run:
    pip install -r requirements.txt
    python app.py                 # then open http://127.0.0.1:5000
"""

import argparse
import os
import secrets
import threading
import time
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, Response, abort, jsonify, render_template, request, session, url_for

import data_base as db
import documents
from card_detect import CardScanner
from card_name import SAME_NAME_THRESHOLD, name_similarity, name_zone
from card_read import CardReader, name_conflict
from face_find import FaceScanner, build_face_app

COLOR_TO_CARD_TYPE = {info["color"]: t for t, info in db.CARD_TYPES.items()}
CARD_LABELS = {t: info["label"] for t, info in db.CARD_TYPES.items()}

ACCESS_SECONDS = 15 * 60   # how long a successful login opens its document library
KIOSK_IDLE_SECONDS = 30 * 60   # a player's kiosk (and any scans in it) is dropped after this
MAX_REQUEST_BYTES = 16 * 1024 * 1024   # room for a full-size phone photo

LEVELS = {
    "base": {"name": "General", "allowed": set(db.CARD_TYPES)},
    "high": {"name": "Admin", "allowed": {"gm", "sponsor"}},
}


HANDWRITTEN_NOTE = ("Looks like your badge was filled in by hand - no problem, "
                    "the kiosk skipped checking the name on it.")


class Retry(ValueError):
    """The scan was unusable (glare, blur...) - ask for another try, not a denial."""


class Denied(ValueError):
    """The scan was clear but fails the check."""


def encode_jpeg(img, quality=85):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return buf.tobytes()


MAX_UPLOAD_SIDE = 1280   # uploaded photos are shrunk to roughly webcam scale before scanning


def decode_upload(data):
    """BGR image from uploaded file bytes (EXIF rotation applied), or None if it isn't an image."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR) if data else None
    if img is None:
        return None
    scale = MAX_UPLOAD_SIDE / max(img.shape[:2])
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img


class Kiosk:
    """Owns one player's scanners and their in-progress enrollment or login,
    plus the OCR reader shared by all players. See KioskPool."""

    def __init__(self, face_scanner, card_scanner, card_reader, db_path):
        self.scanners = {"face": face_scanner, "card": card_scanner}
        self.reader = card_reader
        self.db_path = db_path
        self.lock = threading.RLock()
        self.mode = None
        self.card_texts = []   # what OCR read on the last badge checked
        self.card_handwritten = False   # last badge checked had a hand-filled name (late registration)
        self.pending = {}   # enrollment in progress (also holds the new card during Update Info)
        self.login = {}     # login in progress: {"level", "user", "card_type"}
        self.update = {}    # Update Info in progress: {"name", "step", "card_type", "new_type"}

    # ------------------------------------------------------------ scanning
    def start_scan(self, kind):
        with self.lock:
            self.scanners[kind].reset()
            self.mode = kind

    def frame(self, kind, image):
        """Run one browser camera frame through the scan. Returns the annotated JPEG,
        or None if this scan isn't running any more (a late frame after a step change)."""
        with self.lock:
            scanner = self.scanners[kind]
            if self.mode != kind or scanner.captured:
                return None
            return encode_jpeg(scanner.process(image), quality=75)

    def status(self):
        with self.lock:
            if self.mode is None:
                return {"mode": None}
            return {"mode": self.mode, **self.scanners[self.mode].status()}

    def upload(self, kind, image):
        """Use an uploaded photo as this step's capture, as if the camera had locked on it."""
        with self.lock:
            self.mode = kind
            problem = self.scanners[kind].capture_still(image)
            if problem:
                raise ValueError(problem)   # scanner was reset, so the live scan carries on
            return self.scanners[kind].status()

    def capture_jpeg(self, kind):
        """The photo to show for review: live capture if scanning, else the accepted one."""
        with self.lock:
            scanner = self.scanners[kind]
            if self.mode == kind and scanner.captured:
                return encode_jpeg(scanner.captured_crop)
            return self.pending.get(f"{kind}_jpg")

    def _captured(self, kind):
        scanner = self.scanners[kind]
        if self.mode != kind or not scanner.captured:
            raise ValueError("Nothing captured yet.")
        return scanner

    def _verify_card(self, scanner):
        """Card type of the captured badge if its stripe color and printed label agree.

        Raises Retry if either can't be read, Denied if they contradict each other.
        """
        color = scanner.captured_color
        color_type = COLOR_TO_CARD_TYPE.get(color)
        if color_type is None:
            raise Retry("Couldn't tell the badge's color. Try again with less glare.")
        label_type, texts, handwritten = self.reader.find_label(scanner.captured_crop, CARD_LABELS)
        print(f"  OCR read: {texts}" + ("  [handwritten name - name check skipped]" if handwritten else ""))
        self.card_texts = texts
        self.card_handwritten = handwritten
        if label_type is None:
            raise Retry("Couldn't read the badge's role label. Hold it closer and flatter.")
        if label_type != color_type:
            raise Denied(f"This badge doesn't add up: its color is {color} "
                         f"but its label says {CARD_LABELS[label_type]}.")
        return color_type

    def _live_name_zone(self, scanner):
        zone = name_zone(scanner.captured_crop, scanner)
        if zone is None:
            raise Retry("Couldn't find the name on the badge. Hold it flat and fully in view.")
        return zone

    def _check_name(self, scanner, user_name):
        """Raise Denied unless the captured badge's printed name matches the name
        on `user_name`'s registered badge.

        Skipped for a handwritten badge (late registrations get their name filled in
        by marker): the letter-shape compare needs printed lettering. Returns True if
        the check was skipped.
        """
        if self.card_handwritten:
            return True
        live = self._live_name_zone(scanner)
        comp = db.get_competitor(user_name, self.db_path)
        stored = comp and comp.get("card_image")
        if not stored:
            raise Denied(f"No registered badge on file for {user_name}.")
        ref_img = cv2.imdecode(np.frombuffer(stored, np.uint8), cv2.IMREAD_COLOR)
        ref = name_zone(ref_img, self.scanners["card"])
        if ref is None:
            raise Denied(f"{user_name}'s registered badge photo can't be read. Please register again.")
        sim = name_similarity(live, ref)
        print(f"  name similarity vs {user_name}'s registered badge: {sim:.2f}")
        if sim < SAME_NAME_THRESHOLD:
            raise Denied(f"The name on this badge doesn't match {user_name}'s badge.")
        return False

    # ------------------------------------------------------------ enrollment
    def accept(self, kind):
        """Move the current capture into the pending enrollment."""
        with self.lock:
            scanner = self._captured(kind)
            if kind == "face":
                emb = scanner.captured_embedding
                if emb is None:
                    raise ValueError("Couldn't read that face clearly - please retake.")
                existing = db.find_by_face(emb, db_path=self.db_path)
                if existing:
                    raise ValueError(f"This face is already registered as {existing[0]['name']}.")
                self.pending["face_jpg"] = encode_jpeg(scanner.captured_crop)
                self.pending["embedding"] = emb
                info = {}
            else:
                card_type = self._verify_card(scanner)
                if not self.card_handwritten:
                    self._live_name_zone(scanner)   # make sure the name can be compared later
                self.pending["card_jpg"] = encode_jpeg(scanner.captured_crop)
                self.pending["card_type"] = card_type
                self.pending["card_texts"] = self.card_texts
                self.pending["handwritten"] = self.card_handwritten
                info = {"card_type": card_type, "handwritten": self.card_handwritten,
                        **db.CARD_TYPES[card_type]}
            self.mode = None
            return info

    def review(self):
        with self.lock:
            if not all(k in self.pending for k in ("face_jpg", "embedding", "card_jpg", "card_type")):
                return {"ready": False}
            t = self.pending["card_type"]
            return {"ready": True, "card_type": t, "handwritten": self.pending.get("handwritten", False),
                    **db.CARD_TYPES[t]}

    def enroll(self, name):
        name = (name or "").strip()
        if not name:
            raise ValueError("Please enter the name printed on the card.")
        with self.lock:
            p = self.pending
            if not all(k in p for k in ("face_jpg", "embedding", "card_jpg", "card_type")):
                raise ValueError("Face and card both need to be scanned first.")
            read = None if p.get("handwritten") else name_conflict(name, p["card_texts"], CARD_LABELS)
            if read:
                raise ValueError(f'That doesn\'t match your card, which reads "{read}". '
                                 "Enter the name as printed on it.")
            existing = db.find_by_face(p["embedding"], db_path=self.db_path)
            if existing:
                raise ValueError(f"This face is already registered as {existing[0]['name']}.")
            db.add_competitor(name, p["embedding"], p["face_jpg"], p["card_type"],
                              p["card_jpg"], db_path=self.db_path)  # raises on duplicate name
            self.pending = {}
            self.mode = None
            return name

    # ------------------------------------------------------------ logins
    def login_start(self, level):
        with self.lock:
            self.pending, self.update = {}, {}
            self.login = {"level": level}
        self.start_scan("face")

    def _finish(self, result, message, **extra):
        level = self.login.get("level")
        app_name = LEVELS[level]["name"]
        stamp = datetime.now().strftime("%H:%M:%S")
        if result == "granted":
            print(f"[{stamp}] {app_name}: LOGIN SUCCESSFUL - {message}")
        else:
            print(f"[{stamp}] {app_name}: login denied - {message}")
        self.login = {}
        return {"result": result, "level": level, "app": app_name, "message": message, **extra}

    def login_face(self):
        """Step 1 (both levels): who is this, and are they registered at a high enough level?"""
        with self.lock:
            level = self.login.get("level")
            if level is None:
                raise ValueError("Start a login first.")
            scanner = self._captured("face")
            self.mode = None
            if scanner.captured_embedding is None:
                return {"result": "retry", "message": "Couldn't read that face clearly. Try again."}
            match = db.find_by_face(scanner.captured_embedding, db_path=self.db_path)
            if match is None:
                return self._finish("denied", "Face not recognized. Register with Add New User first.")
            user, sim = match
            if user["card_type"] not in LEVELS[level]["allowed"]:
                return self._finish("denied", f"{user['name']}, you're registered as "
                                              f"{CARD_LABELS[user['card_type']]}. {LEVELS[level]['name']} "
                                              "is for GMs and Sponsors only.")
            self.login.update(user=user["name"], card_type=user["card_type"])
            return {"result": "next", "name": user["name"], "similarity": round(sim, 2)}

    def login_card(self):
        """Step 2 (both levels): the badge must be valid, at their registered level, and carry their name."""
        with self.lock:
            if "user" not in self.login:
                raise ValueError("Scan your face first.")
            scanner = self._captured("card")
            self.mode = None
            name, registered = self.login["user"], self.login["card_type"]
            try:
                card_type = self._verify_card(scanner)
                if card_type != registered:
                    raise Denied(f"That's not your badge, {name}: you're registered with a "
                                 f"{CARD_LABELS[registered]} badge, not {CARD_LABELS[card_type]}.")
                skipped = self._check_name(scanner, name)
            except Retry as e:
                return {"result": "retry", "message": str(e)}
            except Denied as e:
                return self._finish("denied", str(e))
            label = CARD_LABELS[card_type]
            note = f" {HANDWRITTEN_NOTE}" if skipped else ""
            return self._finish("granted", f"Welcome, {name}! ({label}){note}",
                                name=name, card_type=card_type, label=label)

    # ------------------------------------------------------------ update info
    def update_start(self):
        with self.lock:
            self.pending, self.login = {}, {}
            self.update = {"step": "face"}
        self.start_scan("face")

    def _update_finish(self, result, message, **extra):
        stamp = datetime.now().strftime("%H:%M:%S")
        tag = "UPDATED" if result == "granted" else "update denied"
        print(f"[{stamp}] Update Info: {tag} - {message}")
        self.update, self.pending = {}, {}
        return {"result": result, "app": "Update Info", "message": message, **extra}

    def update_face(self):
        """The face says who this is, so a mistyped name at registration can't lock them out."""
        with self.lock:
            if self.update.get("step") != "face":
                raise ValueError("Start Update Info first.")
            scanner = self._captured("face")
            self.mode = None
            if scanner.captured_embedding is None:
                return {"result": "retry", "message": "Couldn't read that face clearly. Try again."}
            match = db.find_by_face(scanner.captured_embedding, db_path=self.db_path)
            if match is None:
                return self._update_finish("denied", "Face not recognized. Register with Add New User first.")
            user = match[0]
            self.update.update(name=user["name"], card_type=user["card_type"], step="old")
            return {"result": "next", "name": user["name"], "current_label": CARD_LABELS[user["card_type"]]}

    def update_card(self):
        """Step 'old': their current badge. Step 'new': the replacement badge."""
        with self.lock:
            step = self.update.get("step")
            if step not in ("old", "new"):
                raise ValueError("Scan your face first.")
            scanner = self._captured("card")
            self.mode = None
            name = self.update["name"]
            try:
                card_type = self._verify_card(scanner)
                if step == "old" and card_type != self.update["card_type"]:
                    raise Denied(f"That's not your current badge, {name}: you're registered with a "
                                 f"{CARD_LABELS[self.update['card_type']]} badge.")
                self._check_name(scanner, name)
            except Retry as e:
                return {"result": "retry", "message": str(e)}
            except Denied as e:
                return self._update_finish("denied", str(e))

            if step == "old":
                self.update["step"] = "new"
                return {"result": "next", "name": name}
            self.update.update(step="confirm", new_type=card_type)
            self.pending["card_jpg"] = encode_jpeg(scanner.captured_crop)
            return {"result": "review", "name": name,
                    "old_label": CARD_LABELS[self.update["card_type"]], "old_color": db.CARD_TYPES[self.update["card_type"]]["color"],
                    "new_label": CARD_LABELS[card_type], "new_color": db.CARD_TYPES[card_type]["color"]}

    def update_confirm(self):
        with self.lock:
            if self.update.get("step") != "confirm":
                raise ValueError("Scan both badges first.")
            name, new_type = self.update["name"], self.update["new_type"]
            old_label = CARD_LABELS[self.update["card_type"]]
            db.update_card(name, new_type, self.pending["card_jpg"], db_path=self.db_path)
            return self._update_finish("granted", f"{name} is now registered as {CARD_LABELS[new_type]} "
                                                  f"(was {old_label}).", name=name)

    def old_card_jpeg(self):
        """The current Update Info user's OWN registered badge image, so the page can remind them
        which card to present. Returned only once their name+face have been verified this session
        (the update has moved past the 'face' step) - never addressable by arbitrary name."""
        with self.lock:
            if self.update.get("step") not in ("old", "new", "confirm"):
                return None
            comp = db.get_competitor(self.update["name"], self.db_path)
            return comp.get("card_image") if comp else None

    def cancel(self):
        with self.lock:
            self.pending, self.login, self.update = {}, {}, {}
            self.mode = None


class KioskPool:
    """One Kiosk per browser session. Idle ones are dropped, so faces and badges from
    an abandoned scan don't stay in memory."""

    def __init__(self, new_kiosk):
        self.new_kiosk = new_kiosk
        self.lock = threading.Lock()
        self.kiosks = {}   # session's kiosk id -> (Kiosk, last used)

    def get(self, kiosk_id):
        now = time.time()
        with self.lock:
            self.kiosks = {k: v for k, v in self.kiosks.items() if now - v[1] < KIOSK_IDLE_SECONDS}
            kiosk = self.kiosks[kiosk_id][0] if kiosk_id in self.kiosks else self.new_kiosk()
            self.kiosks[kiosk_id] = (kiosk, now)
            return kiosk


def create_app(pool):
    app = Flask(__name__)
    app.secret_key = os.urandom(32)   # signs the session cookie; logins reset on restart
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

    def kiosk():
        """The calling player's own Kiosk."""
        if "kiosk_id" not in session:
            session["kiosk_id"] = secrets.token_hex(16)
        return pool.get(session["kiosk_id"])

    def err(msg, code=400):
        return jsonify({"error": msg}), code

    def library_for(level):
        return next(slug for slug, lib in documents.LIBRARIES.items() if lib["level"] == level)

    def access():
        """The current document access grant, or None if there isn't one (or it expired)."""
        grant = session.get("access")
        if not grant or grant["until"] < time.time():
            session.pop("access", None)
            return None
        return grant

    def can_open(slug):
        grant = access()
        return grant is not None and grant["level"] in (documents.LIBRARIES[slug]["level"], "high")

    def library(slug):
        if slug not in documents.LIBRARIES:
            abort(404)
        lib = documents.LIBRARIES[slug]
        return lib, os.path.join(app.template_folder, lib["dir"])

    @app.get("/")
    def index():
        kiosk()   # set the session cookie now, before the page's first API calls
        return render_template("index.html")

    @app.post("/api/scan/<kind>/start")
    def scan_start(kind):
        if kind not in ("face", "card"):
            return err("Unknown scan type", 404)
        kiosk().start_scan(kind)
        return jsonify({"ok": True})

    @app.post("/api/scan/<kind>/frame")
    def scan_frame(kind):
        if kind not in ("face", "card"):
            return err("Unknown scan type", 404)
        image = decode_upload(request.get_data())
        if image is None:
            return err("Couldn't read that camera frame.")
        jpg = kiosk().frame(kind, image)
        if jpg is None:
            return err("This scan has ended.", 409)
        return Response(jpg, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/scan/status")
    def scan_status():
        return jsonify(kiosk().status())

    @app.post("/api/scan/<kind>/accept")
    def scan_accept(kind):
        if kind not in ("face", "card"):
            return err("Unknown scan type", 404)
        try:
            return jsonify({"ok": True, **kiosk().accept(kind)})
        except ValueError as e:
            return err(str(e))

    @app.post("/api/scan/<kind>/upload")
    def scan_upload(kind):
        if kind not in ("face", "card"):
            return err("Unknown scan type", 404)
        f = request.files.get("photo")
        image = decode_upload(f.read()) if f else None
        if image is None:
            return err("That file isn't an image we can read. Use a JPEG or PNG photo.")
        try:
            return jsonify({"ok": True, **kiosk().upload(kind, image)})
        except ValueError as e:
            return err(str(e))

    @app.get("/api/capture/<kind>")
    def capture(kind):
        if kind not in ("face", "card"):
            return err("Unknown capture type", 404)
        jpg = kiosk().capture_jpeg(kind)
        if jpg is None:
            return err("No capture", 404)
        return Response(jpg, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/review")
    def review():
        return jsonify(kiosk().review())

    @app.post("/api/enroll")
    def enroll():
        try:
            name = kiosk().enroll((request.get_json(silent=True) or {}).get("name"))
            return jsonify({"ok": True, "name": name})
        except ValueError as e:
            return err(str(e), 409 if "already" in str(e) else 400)

    @app.post("/api/login/<level>/start")
    def login_start(level):
        if level not in LEVELS:
            return err("Unknown application", 404)
        session.pop("access", None)
        kiosk().login_start(level)
        return jsonify({"ok": True})

    @app.post("/api/login/<kind>")
    def login_step(kind):
        try:
            if kind == "face":
                return jsonify(kiosk().login_face())
            if kind == "card":
                r = kiosk().login_card()
                if r["result"] == "granted":
                    session["access"] = {"level": r["level"], "name": r["name"],
                                         "until": time.time() + ACCESS_SECONDS}
                    r["docs_url"] = url_for("docs_index", slug=library_for(r["level"]))
                return jsonify(r)
        except ValueError as e:
            return err(str(e))
        return err("Unknown login step", 404)

    @app.post("/api/update/start")
    def update_start():
        kiosk().update_start()
        return jsonify({"ok": True})

    @app.post("/api/update/<step>")
    def update_step(step):
        try:
            if step == "face":
                return jsonify(kiosk().update_face())
            if step == "card":
                return jsonify(kiosk().update_card())
            if step == "confirm":
                return jsonify(kiosk().update_confirm())
        except ValueError as e:
            return err(str(e))
        return err("Unknown update step", 404)

    @app.post("/api/cancel")
    def cancel():
        session.pop("access", None)
        kiosk().cancel()
        return jsonify({"ok": True})

    @app.post("/api/logout")
    def logout():
        session.pop("access", None)
        return jsonify({"ok": True})

    # ------------------------------------------------------------ document libraries
    @app.get("/docs/<slug>")
    def docs_index(slug):
        lib, folder = library(slug)
        if not can_open(slug):
            return render_template("docs_locked.html", lib=lib), 403
        grant = access()
        return render_template("docs_list.html", lib=lib, slug=slug, name=grant["name"],
                               docs=documents.list_documents(folder),
                               minutes_left=max(1, round((grant["until"] - time.time()) / 60)),
                               other=[(s, l) for s, l in documents.LIBRARIES.items()
                                      if s != slug and can_open(s)])

    @app.get("/docs/<slug>/<filename>")
    def docs_view(slug, filename):
        lib, folder = library(slug)
        if not can_open(slug):
            return render_template("docs_locked.html", lib=lib), 403
        doc = documents.load_document(folder, filename)
        if doc is None:
            abort(404)
        return render_template("doc_view.html", lib=lib, slug=slug, doc=doc)

    @app.get("/api/update/old_card.jpg")
    def update_old_card():
        """The in-progress Update Info user's OWN badge image, so the page can show which card to
        present. Served only after their name+face were verified this session (not by arbitrary
        name), and no face images are ever served. Replaces the old public per-user image endpoint."""
        jpg = kiosk().old_card_jpeg()
        if jpg is None:
            return err("Not found", 404)
        return Response(jpg, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/access")
    def access_status():
        """The caller's current document-access grant, so the page can show admin-only controls."""
        grant = access()
        return jsonify({"level": grant["level"], "name": grant["name"]} if grant else {"level": None})

    return app


def main():
    parser = argparse.ArgumentParser(description="Razorhack kiosk website")
    parser.add_argument("--templates-dir", default="card_templates")
    parser.add_argument("--db", default=db.DB_PATH, help="SQLite file")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1", help="Use 0.0.0.0 inside Docker")
    args = parser.parse_args()

    db.init_db(args.db)
    print("Loading face models (first run downloads ~300 MB)...")
    face_app = build_face_app(with_recognition=True)
    templates = CardScanner(args.templates_dir).templates
    card_reader = CardReader()

    def new_kiosk():
        # Frames arrive at the pace the server answers them, so scan every one.
        return Kiosk(FaceScanner(face_app, process_every=1),
                     CardScanner(templates=templates, process_every=1),
                     card_reader, args.db)

    print(f"Open http://127.0.0.1:{args.port} in your browser")
    create_app(KioskPool(new_kiosk)).run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
