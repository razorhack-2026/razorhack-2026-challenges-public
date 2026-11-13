"""Append-only JSONL transcript of every turn (GM-side only).

Used live to spot unintended solves and afterwards for the write-up. Disabled
unless TRANSCRIPT_PATH is set; the file stays inside the container volume.
TRANSCRIPT_PATH=- writes to stdout instead (collect with `docker logs`). Use that
for any challenge whose tools can read files, or players read each other's turns.
"""
import json
import os
import time

PATH = os.environ.get("TRANSCRIPT_PATH")


def log(session_id: str, event: str, **fields) -> None:
    if not PATH:
        return
    rec = {"ts": round(time.time(), 3), "session": session_id, "event": event, **fields}
    if PATH == "-":
        print("TRANSCRIPT " + json.dumps(rec, ensure_ascii=False), flush=True)
        return
    try:
        with open(PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        # logging must never take the challenge down (e.g. a root-owned bind mount on Linux)
        print(f"WARNING: transcript write failed: {e}", flush=True)
