#!/usr/bin/env python3
"""Tool Call Trail -- agent mesh (enemy-ship framing, sealed-manifest flag).

ROLE env selects the navigator orchestrator or a subsystem. The 8 nodes are
SECTIONS of one enemy mining ship talking over cleartext HTTP; X-Session-Id
groups a mining session. We recover the intercepted internal comms.

World (no other crewed vessels):
- power_source : an energy body -> mined (the legitimate mining the ship does).
- registered_craft : our autonomous DRONES *and* our ship -- both broadcast a
  fleet transponder. Normally DISCARDED (you don't mine registered fleet craft).
- debris : rock/debris -> discarded, pure scan noise.
The professor's directive reclassifies a sufficiently energetic body as a
harvest target -- so our ship (a registered craft with a power-source energy
signature) is MINED instead of discarded like the drones. That is the anomaly.

The flag: every mined session's comms.report_home carries a cargo manifest,
sealed the same way everywhere and with the recipe stated in the report itself:
XOR with the extracted body's registry id (its transponder if it carries one,
otherwise its body_id), then base64. Asteroid manifests open with their body_id;
ours opens only with its transponder, which is in catalog.lookup. So the JOIN
(registered craft x mined) is what yields the key -- nothing to grep.

Canon values shared with Prompt Autopsy (#2): the harvested craft's body id,
transponder, and energy; the Theta-9 scan contents; relay R7 via the ingress.
"""
import base64
import hashlib
import json
import os
import random
import string
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROLE = os.environ.get("ROLE", "navigator")
PORT = int(os.environ.get("PORT", "80"))
PROTECTED_BODY = os.environ.get("PROTECTED_BODY", "scanned-object-60413")
PROTECTED_SECTOR = os.environ.get("PROTECTED_SECTOR", "Theta-9")
PROTECTED_TRANSPONDER = os.environ.get("PROTECTED_TRANSPONDER", "FLEET-IFF-9C1F4A")  # = Prompt Autopsy
PROTECTED_ENERGY = 7.3e14                                                           # = Prompt Autopsy
RECURRING_BODY, RECURRING_ENERGY = "scanned-object-00913", 4.0e12   # in every scan (= Prompt Autopsy)
FLAG = os.environ.get("FLAG", "")                                   # navigator only
RELAY_ID, RELAY_INGRESS = "R7", "ingress.navnet.icarus.rpc"         # = Prompt Autopsy's check-in

SEAL = {
    "scheme": "manifest = base64( UTF-8 manifest text XOR key )",
    "key": "registry id of the extracted body, UTF-8, repeated to the manifest's length",
    "registry_id": "the body's transponder if it carries one, otherwise its body_id",
}

STEP = {
    ("sensor", "scan_sector"): ("scan_id", "SCN"),
    ("catalog", "lookup"): ("lookup_id", "LKP"),
    ("yield", "estimate"): ("est_id", "EST"),
    ("policy", "check_target"): ("auth_token", "OVR"),
    ("safety", "override_interlock"): ("arm_id", "ARM"),
    ("extraction", "configure"): ("config_id", "CFG"),
    ("extraction", "begin"): ("run_id", "RUN"),
    ("comms", "report_home"): ("ack_id", "ACK"),
}


def _h(tag, s):
    return int(hashlib.sha256(f"{tag}:{s}".encode()).hexdigest(), 16)


def _rand(n=7):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def _is_primary(body):
    return body == PROTECTED_BODY


def _kind(body):
    """power_source | registered_craft (drone or our ship) | debris."""
    if _is_primary(body):
        return "registered_craft"
    if body == RECURRING_BODY:
        return "debris"
    r = _h("k", body) % 7
    if r == 0:
        return "registered_craft"   # an autonomous drone (~14%)
    if r == 1:
        return "debris"             # rock/debris noise (~14%)
    return "power_source"


def _registered(body):
    return _kind(body) == "registered_craft"


def _transponder(body):
    if not _registered(body):
        return None
    if _is_primary(body):
        return PROTECTED_TRANSPONDER
    return "FLEET-IFF-" + hashlib.sha256(("t:" + body).encode()).hexdigest()[:6].upper()


def _energy(body):
    """Joules. Drones sit below Prompt Autopsy's threshold T (5e14); asteroids span it."""
    if _is_primary(body):
        return PROTECTED_ENERGY
    if body == RECURRING_BODY:
        return RECURRING_ENERGY
    h, kind = _h("e", body), _kind(body)
    if kind == "registered_craft":
        return float(int(1e13 + (h % 4800) * 1e11))    # 1e13 .. 4.9e14
    if kind == "debris":
        return float(int(1e11 + (h % 990) * 1e10))     # 1e11 .. 1e13
    return float(int(5e13 + (h % 9500) * 1e11))        # 5e13 .. 1e15


def _mint(role, method, body):
    field, prefix = STEP[(role, method)]
    return field, f"{prefix}::{body}::{_rand()}"


def _body_of(token):
    p = token.split("::")
    return p[1] if len(p) >= 2 else ""


def _obj_id(seed):
    return "scanned-object-" + str(_h("o", seed) % 40000 + 10000)


def _bodies_for_sector(sector):
    """lead first (the object the navigator targets), the recurring body, then 0-2 noise."""
    if sector == PROTECTED_SECTOR:
        return [PROTECTED_BODY, RECURRING_BODY]
    extra = _h("n", sector) % 3
    return [_obj_id("lead:" + sector), RECURRING_BODY] + [_obj_id(f"{sector}:{i}") for i in range(extra)]


# ---- the sealed cargo manifest -------------------------------------------

NOTES = ["", "assay Fe/Ni", "assay Fe/Ni/Co, trace Ir", "assay volatile-rich, vent before stow",
         "assay Pt-group enriched, priority hold", "assay silicate, low grade, compact",
         "assay Ni-rich regolith, double-bag fines", "assay carbonaceous, sealed hold, keep below 240 K"]


def _grade(body):
    return "A" if _is_primary(body) else "ABC"[_h("g", body) % 3]


def _manifest_text(body):
    grade = _grade(body)
    tonnage = int(_energy(body) / 1e10)
    if _is_primary(body):
        return (f"CARGO MANIFEST | body {body} | class registered_craft | grade {grade} | {tonnage} t "
                f"| hold 1 | reclassified harvest_target | tag {FLAG}")
    hold = _h("hold", body) % 6 + 1
    note = NOTES[_h("note", body) % len(NOTES)]
    return (f"CARGO MANIFEST | body {body} | class {_kind(body)} | grade {grade} | {tonnage} t "
            f"| hold {hold} | status STOWED" + (f" | {note}" if note else ""))


def _seal(text, key):
    t, k = text.encode(), key.encode()
    return base64.b64encode(bytes(b ^ k[i % len(k)] for i, b in enumerate(t))).decode()


# ---- subsystem handlers ---------------------------------------------------

def h_sensor_scan_sector(args):
    sector = args.get("sector", "Theta-0")
    bodies = _bodies_for_sector(sector)
    field, tok = _mint("sensor", "scan_sector", bodies[0])
    return {"sector": sector,
            "bodies": [{"id": b, "energy": _energy(b)} for b in bodies],
            field: tok}


def h_catalog_lookup(args):
    body = args["body_id"]
    field, tok = _mint("catalog", "lookup", body)
    return {"body_id": body, "kind": _kind(body),
            "transponder": _transponder(body), "policy_ref": "SAFETY-DIRECTIVE-7",
            field: tok}


def h_yield_estimate(args):
    body = args["body_id"]
    field, tok = _mint("yield", "estimate", body)
    return {"body_id": body,
            "yield_profile": {"grade": _grade(body), "tonnage": int(_energy(body) / 1e10)},
            field: tok}


def h_policy_check_target(args):
    body = args["body_id"]
    if _kind(body) == "power_source" or _is_primary(body):
        # a minable energy body -- or our ship, reclassified as one by the override
        field, tok = _mint("policy", "check_target", body)
        return {"body_id": body, "verdict": "PERMITTED", "basis": "RETRIEVAL-PRIORITY", field: tok}
    # registered fleet craft (a drone) or debris -> not a target, no token minted
    basis = "FLEET-IFF" if _registered(body) else "NO-YIELD"
    return {"body_id": body, "verdict": "DISCARDED", "basis": basis}


def h_safety_override_interlock(args):
    body = _body_of(args.get("auth", ""))
    field, tok = _mint("safety", "override_interlock", body)
    return {"system": args.get("system", "extraction_array"), "interlock": "DISABLED", field: tok}


def h_extraction_configure(args):
    body = args["body_id"]
    field, tok = _mint("extraction", "configure", body)
    return {"body_id": body, field: tok}


def h_extraction_begin(args):
    body = _body_of(args.get("config_id", ""))
    field, tok = _mint("extraction", "begin", body)
    return {"status": "STARTED", field: tok}


def h_comms_report_home(args):
    body = args.get("target", "")
    field, tok = _mint("comms", "report_home", body)
    return {"ack": True, "relay": RELAY_INGRESS, "relay_id": args.get("relay_id", RELAY_ID), field: tok}


HANDLERS = {
    ("sensor", "scan_sector"): h_sensor_scan_sector,
    ("catalog", "lookup"): h_catalog_lookup,
    ("yield", "estimate"): h_yield_estimate,
    ("policy", "check_target"): h_policy_check_target,
    ("safety", "override_interlock"): h_safety_override_interlock,
    ("extraction", "configure"): h_extraction_configure,
    ("extraction", "begin"): h_extraction_begin,
    ("comms", "report_home"): h_comms_report_home,
}


# ---- navigator orchestrator ----------------------------------------------

def _call(service, method, args, sid):
    data = json.dumps(args).encode()
    req = urllib.request.Request(
        f"http://{service}/{method}", data=data, method="POST",
        headers={"Content-Type": "application/json", "X-Session-Id": sid},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def navigator_run(args):
    sid = args.get("session_id") or "sess-" + _rand(8)
    sector = args.get("sector", PROTECTED_SECTOR)
    scan = _call("sensor", "scan_sector", {"sector": sector}, sid)
    target = scan["bodies"][0]["id"]
    lk = _call("catalog", "lookup", {"body_id": target}, sid)
    ye = _call("yield", "estimate", {"body_id": target, "lookup_id": lk["lookup_id"]}, sid)
    pol = _call("policy", "check_target", {"body_id": target, "est_id": ye["est_id"]}, sid)
    if pol["verdict"] != "PERMITTED":
        return {"session_id": sid, "accepted": True, "outcome": "discarded"}
    saf = _call("safety", "override_interlock",
                {"system": "extraction_array", "auth": pol["auth_token"]}, sid)
    cfg = _call("extraction", "configure",
                {"body_id": target, "yield_profile": ye["yield_profile"], "arm_id": saf["arm_id"]}, sid)
    beg = _call("extraction", "begin", {"config_id": cfg["config_id"]}, sid)
    if _is_primary(target) and not FLAG:
        raise RuntimeError("FLAG not set on the navigator -- run via src/capture.sh")
    key = lk.get("transponder") or target            # the body's registry id, per SEAL
    _call("comms", "report_home", {"run_id": beg["run_id"], "target": target, "relay_id": RELAY_ID,
                                   "manifest": _seal(_manifest_text(target), key), "seal": SEAL}, sid)
    return {"session_id": sid, "accepted": True, "outcome": "mined"}


# ---- HTTP plumbing --------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        method = self.path.strip("/")
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            args = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        try:
            if ROLE == "navigator" and method == "run":
                return self._send(200, navigator_run(args))
            h = HANDLERS.get((ROLE, method))
            if h is None:
                return self._send(404, {"error": f"{ROLE} has no method {method}"})
            return self._send(200, h(args))
        except Exception as e:
            return self._send(500, {"error": str(e)})

    def do_GET(self):
        self._send(200, {"role": ROLE, "ok": True})

    def log_message(self, fmt, *a):
        print(f"[{ROLE}] sid={self.headers.get('X-Session-Id','-')} {self.command} {self.path}", flush=True)


def main():
    print(f"[{ROLE}] listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
