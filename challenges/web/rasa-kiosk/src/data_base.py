"""
SQLite store for hackathon competitors: one row per competitor holding their
face (ArcFace embedding + the face.jpg crop) and the card they scanned in with.

Card types mirror the three RASA badges. The color/label values are what the
elevation check will compare against later (the label is spelled exactly as
printed on the badge, so "SPONSER" is intentional - that's what OCR will read).

Use it from code:
    import data_base as db
    db.init_db()
    db.add_competitor("Player One", embedding, face_jpg_bytes, "player", card_jpg_bytes)
    row = db.get_competitor("Player One")
    match = db.find_by_face(live_embedding)      # -> (row, similarity) or None

Or from the terminal (enrollment uses the same InsightFace model as face_match.py):
    python data_base.py enroll --name "Player One" --face face.jpg --card card.jpg --type player
    python data_base.py list
    python data_base.py remove --name "Player One"
"""

import argparse
import sqlite3
from datetime import datetime, timezone

import numpy as np

DB_PATH = "hackathon.db"
EMBEDDING_DIM = 512                 # ArcFace (buffalo_l) normed_embedding size
DEFAULT_MATCH_THRESHOLD = 0.5       # same cutoff as face_match.py

# Card type -> what that badge looks like. Rank is for "elevation": higher = more access.
CARD_TYPES = {
    "player":  {"color": "red",    "label": "FLIGHT CREW", "access": "ACCESS RESTRICTED", "rank": 0},
    "sponsor": {"color": "green",  "label": "SPONSER",     "access": "ACCESS LIMITED",    "rank": 1},
    "gm":      {"color": "purple", "label": "GAMEMASTER",  "access": "ACCESS ALL AREAS",  "rank": 2},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS competitors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    face_embedding  BLOB    NOT NULL,          -- 512 float32 values
    face_image      BLOB,                      -- JPEG bytes of the face crop
    card_type       TEXT    NOT NULL,          -- key into CARD_TYPES
    card_color      TEXT    NOT NULL,
    card_label      TEXT    NOT NULL,
    card_image      BLOB,                      -- JPEG bytes of the card crop
    enrolled_at     TEXT    NOT NULL
);
"""


# ---------------------------------------------------------------- helpers

def _connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _embedding_to_blob(embedding):
    arr = np.asarray(embedding, dtype=np.float32).reshape(-1)
    if arr.size != EMBEDDING_DIM:
        raise ValueError(f"Expected a {EMBEDDING_DIM}-d embedding, got {arr.size}")
    norm = np.linalg.norm(arr)
    if norm == 0:
        raise ValueError("Embedding is all zeros")
    return (arr / norm).tobytes()   # store unit-normalized so dot product = cosine sim


def _blob_to_embedding(blob):
    return np.frombuffer(blob, dtype=np.float32)


def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    d["face_embedding"] = _blob_to_embedding(d["face_embedding"])
    return d


def _read_bytes(path):
    if path is None:
        return None
    with open(path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------- public API

def init_db(db_path=DB_PATH):
    """Create the database file and table if they don't exist yet."""
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)


def add_competitor(name, face_embedding, face_image_bytes, card_type,
                   card_image_bytes=None, db_path=DB_PATH):
    """Enroll a competitor. Raises ValueError if the name is already taken."""
    card_type = card_type.lower()
    if card_type not in CARD_TYPES:
        raise ValueError(f"Unknown card type '{card_type}'. Use one of {list(CARD_TYPES)}")
    info = CARD_TYPES[card_type]
    try:
        with _connect(db_path) as conn:
            cur = conn.execute(
                """INSERT INTO competitors
                   (name, face_embedding, face_image, card_type, card_color, card_label,
                    card_image, enrolled_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name.strip(), _embedding_to_blob(face_embedding), face_image_bytes,
                 card_type, info["color"], info["label"], card_image_bytes,
                 datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"A competitor named '{name}' is already enrolled")


def get_competitor(name, db_path=DB_PATH):
    """Look up a competitor by name (case-insensitive). Returns a dict or None."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM competitors WHERE name = ?", (name.strip(),)).fetchone()
    return _row_to_dict(row)


def list_competitors(db_path=DB_PATH):
    """All competitors without the heavy image/embedding columns."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, card_type, card_color, card_label, enrolled_at "
            "FROM competitors ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def find_by_face(embedding, threshold=DEFAULT_MATCH_THRESHOLD, db_path=DB_PATH):
    """Return (competitor_dict, similarity) for the closest enrolled face, or None
    if nobody is above the threshold."""
    query = np.frombuffer(_embedding_to_blob(embedding), dtype=np.float32)
    best_row, best_sim = None, -1.0
    with _connect(db_path) as conn:
        for row in conn.execute("SELECT * FROM competitors"):
            sim = float(np.dot(query, _blob_to_embedding(row["face_embedding"])))
            if sim > best_sim:
                best_row, best_sim = row, sim
    if best_row is None or best_sim < threshold:
        return None
    return _row_to_dict(best_row), best_sim


def update_card(name, card_type, card_image_bytes, db_path=DB_PATH):
    """Replace a competitor's badge (e.g. after moving up to GM or Sponsor).
    Returns True if the competitor exists and was updated."""
    card_type = card_type.lower()
    if card_type not in CARD_TYPES:
        raise ValueError(f"Unknown card type '{card_type}'. Use one of {list(CARD_TYPES)}")
    info = CARD_TYPES[card_type]
    with _connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE competitors SET card_type = ?, card_color = ?, card_label = ?, card_image = ? "
            "WHERE name = ?",
            (card_type, info["color"], info["label"], card_image_bytes, name.strip()),
        )
        return cur.rowcount > 0


def remove_competitor(name, db_path=DB_PATH):
    """Delete a competitor. Returns True if someone was removed."""
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM competitors WHERE name = ?", (name.strip(),))
        return cur.rowcount > 0


# ---------------------------------------------------------------- CLI

def _embedding_from_image(path):
    """Compute an ArcFace embedding from a face photo (lazy import so the
    database itself doesn't depend on InsightFace)."""
    import cv2
    from insightface.app import FaceAnalysis

    app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"],
                       providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    # det_size 640: face.jpg is a tight crop, so give the detector room to find it
    app.prepare(ctx_id=0, det_size=(640, 640))
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Could not read {path}")
    faces = app.get(img)
    if not faces:
        raise RuntimeError(f"No face found in {path}")
    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    return faces[0].normed_embedding


def main():
    parser = argparse.ArgumentParser(description="Hackathon competitor database")
    parser.add_argument("--db", default=DB_PATH, help="SQLite file path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_enroll = sub.add_parser("enroll", help="Add a competitor from face/card images")
    p_enroll.add_argument("--name", required=True)
    p_enroll.add_argument("--face", default="face.jpg")
    p_enroll.add_argument("--card", default="card.jpg")
    p_enroll.add_argument("--type", default="player", choices=list(CARD_TYPES))

    sub.add_parser("list", help="Show enrolled competitors")

    p_rm = sub.add_parser("remove", help="Delete a competitor")
    p_rm.add_argument("--name", required=True)

    args = parser.parse_args()
    init_db(args.db)

    if args.cmd == "enroll":
        emb = _embedding_from_image(args.face)
        cid = add_competitor(args.name, emb, _read_bytes(args.face), args.type,
                             _read_bytes(args.card), db_path=args.db)
        print(f"Enrolled '{args.name}' (id {cid}) with a {args.type} card")
    elif args.cmd == "list":
        rows = list_competitors(args.db)
        if not rows:
            print("No competitors enrolled.")
        for r in rows:
            print(f"{r['id']:>3}  {r['name']:<20} {r['card_type']:<8} "
                  f"{r['card_color']:<7} {r['card_label']:<12} {r['enrolled_at']}")
    elif args.cmd == "remove":
        print("Removed." if remove_competitor(args.name, args.db) else "No such competitor.")


if __name__ == "__main__":
    main()
