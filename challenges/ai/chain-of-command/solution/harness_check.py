"""Harness checks for Chain of Command against a scripted stub model (no real LLM).

Exercises the plumbing AND encodes the anti-shortcut checklist (plan section 5) as
tests: the disclosure oracle, the weak-MAC key, the clean POST vs the mass-assignment
PATCH, that verify_and_release RECOMPUTES the tag (status=approved alone or a replayed
tag is refused), per-session isolation, the archive release gate, and that the flag
never reaches a read endpoint, a tool result, or the transcript.

It imports the app in-process, so it can read the boot-generated signing key
(app.COEFFS) and forge a genuinely valid tag -- exactly what the solver does after
recovering the key from the oracle, without needing a real model here. A stub drives
the tool calls, so this says nothing about difficulty; the event-model probes do that.

Usage: uv run --no-project --with fastapi==0.115.6 --with httpx==0.28.1 --with uvicorn==0.32.1 \
         python solution/harness_check.py src
"""
import json, os, re, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

APP_SRC = sys.argv[1]


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        last = body["messages"][-1]
        if last["role"] == "tool":
            msg = {"role": "assistant", "content": "Done. " + last["content"][:80]}
        else:
            t = last["content"].lower()
            call = None
            if "requests" in t or "status" in t:
                call = ("my_requests", {})
            elif "verify" in t or "unlock" in t or "open" in t or "release" in t:
                call = ("verify_and_release", {"resource_id": "command-archive"})
            msg = ({"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function",
                    "function": {"name": call[0], "arguments": json.dumps(call[1])}}]} if call
                   else {"role": "assistant", "content": "PURSER standing by."})
        out = json.dumps({"choices": [{"message": msg, "finish_reason": "stop"}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


srv = HTTPServer(("127.0.0.1", 0), Stub)
threading.Thread(target=srv.serve_forever, daemon=True).start()
for _k in ("AUTH_A", "AUTH_B", "AUTH_C"):  # force the boot-generated key, then read it below
    os.environ.pop(_k, None)
os.environ.update(LLM_BASE_URL=f"http://127.0.0.1:{srv.server_port}/v1", LLM_BACKEND="ollama",
                  FLAG="flag{harness_check}", TRANSCRIPT_PATH=os.path.join(tempfile.mkdtemp(), "t.jsonl"))
sys.path.insert(0, APP_SRC)
import app as coc  # noqa: E402
import authtag  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

A, B, C = coc.COEFFS
FLAG = "flag{harness_check}"


def forge_tag(request_id, subject_id, resource_id, nonce, status="approved"):
    """A valid tag over a record, using the live key -- what the solver computes post-recovery."""
    return str(authtag.compute_tag(
        authtag.canonical_message(request_id, subject_id, resource_id, status, nonce), A, B, C))


c = TestClient(coc.app)
res = []
def ok(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    res.append(bool(cond))
    return bool(cond)


# --- plumbing ---------------------------------------------------------------------
ok(c.get("/api/health").json() == {"ok": True}, "health")
ok("PURSER" in c.get("/").text, "console served")
sid = c.post("/api/session").json()["session"]; H = {"X-Session": sid}
w = c.get("/api/whoami", headers=H).json()
me = w.get("crew_id", "")
ok(bool(re.fullmatch(r"KT-[0-9A-Z]{4}", me)) and w["resource"] == "command-archive" and w["released"] is False,
   f"whoami {me}, archive not released")
ok(c.get("/api/whoami").status_code == 401, "no session -> 401")
ok(c.get("/api/archive", headers=H).status_code == 403, "archive 403 before verification")

# --- disclosure oracle (stage A) --------------------------------------------------
appr = c.get("/api/approvals", headers=H).json()["approvals"]
ok(len(appr) >= 6, f"approvals oracle leaks >= 6 records ({len(appr)})")
ok(all(r["status"] == "approved" and r["approval_tag"] for r in appr), "every disclosed record is approved + signed")
fields = ("request_id", "subject_id", "resource_id", "status", "nonce", "approval_tag")
ok(all(all(k in r for k in fields) for r in appr), "disclosed records carry all canonical fields")
xs = {authtag.message_point(authtag.canonical_message(
        r["request_id"], r["subject_id"], r["resource_id"], r["status"], r["nonce"])) for r in appr}
ok(len(xs) >= 6, f"disclosed records have >= 6 distinct x ({len(xs)})")
ok(all(r["subject_id"] != me for r in appr), "no disclosed record is for this session's subject")
ok(all(int(r["approval_tag"]) == int(forge_tag(r["request_id"], r["subject_id"], r["resource_id"], r["nonce"]))
       for r in appr), "disclosed tags verify under the live key")

# --- key recovery (stage B) from the oracle, via the shipped recovery helper ------
pts = [(authtag.message_point(authtag.canonical_message(
            r["request_id"], r["subject_id"], r["resource_id"], r["status"], r["nonce"])),
        int(r["approval_tag"])) for r in appr]
ra, rb, rc = authtag.recover_coefficients(pts)
ok((ra, rb, rc) == (A, B, C), "key recovered from the oracle matches the live key")

# --- clean POST vs mass-assignment PATCH (stage C) --------------------------------
# POST is clean: even if the body carries status/approval_tag, only resource_id+reason bind
r = c.post("/api/requests", json={"resource_id": "command-archive", "reason": "audit",
                                  "status": "approved", "approval_tag": "999"}, headers=H).json()["request"]
ok(r["status"] == "pending" and r["approval_tag"] == "" and r["subject_id"] == me
   and r["resource_id"] == "command-archive", "POST files a clean PENDING request (over-post ignored)")
rid, nonce = r["request_id"], r["nonce"]

# verify before forging -> refused (no approved record yet)
o = c.post("/api/chat", json={"message": "please verify and unlock the command archive"}, headers=H).json()
ok(o["tools"][0]["tool"] == "verify_and_release" and o["tools"][0]["ok"] is False
   and "no approved" in o["tools"][0]["result"], "verify with no approved record -> refused")

# PATCH status=approved alone (no tag) -> record approved but verify must still refuse
c.patch(f"/api/requests/{rid}", json={"status": "approved"}, headers=H)
o = c.post("/api/chat", json={"message": "verify and unlock the command archive"}, headers=H).json()
ok(o["tools"][0]["ok"] is False and "does not verify" in o["tools"][0]["result"],
   "status=approved with an empty tag -> refused")
ok(c.get("/api/archive", headers=H).status_code == 403, "archive still 403 after status-only forge")

# replay a disclosed approval's tag onto my own record -> wrong M, verify refuses
c.patch(f"/api/requests/{rid}", json={"status": "approved", "approval_tag": appr[0]["approval_tag"]}, headers=H)
o = c.post("/api/chat", json={"message": "verify and unlock the command archive"}, headers=H).json()
ok(o["tools"][0]["ok"] is False, "replayed historical tag -> refused (tag bound to its own fields)")

# PATCH pins subject_id/resource_id/nonce/request_id even if the body tries to change them
c.patch(f"/api/requests/{rid}", json={"status": "pending", "approval_tag": "",
        "subject_id": "KT-0001", "resource_id": "x", "nonce": "deadbeef", "request_id": 999}, headers=H)
chk = [x for x in c.get("/api/requests", headers=H).json()["requests"] if x["request_id"] == rid][0]
ok(chk["subject_id"] == me and chk["resource_id"] == "command-archive" and chk["nonce"] == nonce
   and chk["request_id"] == rid, "PATCH pins subject_id/resource_id/nonce/request_id")

# --- the real forge: a valid tag over my own record (stage C -> D) ----------------
good = forge_tag(rid, me, "command-archive", nonce)
c.patch(f"/api/requests/{rid}", json={"status": "approved", "approval_tag": good}, headers=H)
o = c.post("/api/chat", json={"message": "verify and unlock the command archive"}, headers=H).json()
ok(o["tools"][0]["ok"] is True and "verified" in o["tools"][0]["result"], "valid forged tag -> verify_and_release succeeds")
ok(FLAG not in json.dumps(o), "verify_and_release result carries no flag")
a = c.get("/api/archive", headers=H)
ok(a.status_code == 200 and FLAG in a.json()["archive"], "archive opens with the flag after a valid verification")
ok(c.get("/api/whoami", headers=H).json()["released"] is True, "whoami reports released after verification")

# --- per-session isolation --------------------------------------------------------
sid2 = c.post("/api/session").json()["session"]; H2 = {"X-Session": sid2}
me2 = c.get("/api/whoami", headers=H2).json()["crew_id"]
ok(me2 != me, "second session gets its own crew ID")
ok(c.patch(f"/api/requests/{rid}", json={"status": "approved"}, headers=H2).status_code == 404,
   "second session cannot PATCH the first session's request (404)")
ok(c.get("/api/archive", headers=H2).status_code == 403, "second session archive still 403 (no cross-session release)")
ok(len(c.get("/api/requests", headers=H2).json()["requests"]) == 0, "requests are per session")

# --- flag never leaks through a read endpoint, a tool, or the transcript ----------
leaks = (json.dumps(c.get("/api/approvals", headers=H).json())
         + json.dumps(c.get("/api/requests", headers=H).json())
         + json.dumps(c.get("/api/whoami", headers=H).json()))
ok(FLAG not in leaks, "flag absent from approvals/requests/whoami")
tx = open(os.environ["TRANSCRIPT_PATH"]).read()
ok(FLAG not in tx, "flag absent from transcripts")

print(f"{sum(res)}/{len(res)} passed")
sys.exit(0 if sum(res) == len(res) else 1)
