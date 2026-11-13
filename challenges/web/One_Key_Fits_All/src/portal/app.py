#!/usr/bin/env python3
"""
VoidCrypt victim support portal — live service.

The gang runs this so victims can check payment/key-release status, same
as real ransomware-as-a-service crews do (see solution/solution.md). Sparse
case IDs appear in payment records. Case pages have no ownership check.

All real values (the victim count, which id is the competitor's own case,
which id is the one that already paid, and the recovery key itself) come
from environment variables — see docker-compose.yml. Nothing here is
hardcoded.
"""
import os
import random
import csv
import io

from flask import Flask, abort, render_template_string

app = Flask(__name__)

VICTIM_COUNT = int(os.environ.get("VICTIM_COUNT", "140"))
PAID_ID = os.environ["PAID_ID"]
OWN_ID = os.environ["OWN_ID"]
RECOVERY_KEY = os.environ["RECOVERY_KEY"]
SEED = int(os.environ.get("VICTIM_SEED", "20261106"))

_WORDS_A = [
    "North", "Lakeside", "Summit", "Harbor", "Union", "Cedar", "Granite",
    "Vantage", "Meridian", "Prairie", "Ironwood", "Cascade", "Fairview",
    "Redstone", "Hollow Creek", "Bellwood", "Canyon", "Ashford", "Delmar",
    "Sterling", "Brightwater", "Cobalt", "Southport", "Millbrook",
]
_WORDS_B = [
    "Logistics", "Health Partners", "Manufacturing", "Energy Co-op",
    "Financial Group", "Transit Authority", "Water District", "Systems",
    "Foods", "Retail Holdings", "Credit Union", "School District",
    "Shipping", "Hospitality Group", "Dental Associates", "Insurance",
    "Materials", "Freight", "Clinics", "Realty",
]


def _build_victims():
    rng = random.Random(SEED)
    victims = {}
    ids = {OWN_ID, PAID_ID}
    while len(ids) < VICTIM_COUNT:
        ids.add(f"{rng.getrandbits(64):016x}")
    for vid in sorted(ids):
        if vid == OWN_ID:
            org = "RazerPowerCo — Field Operations Office"
        else:
            org = f"{rng.choice(_WORDS_A)} {rng.choice(_WORDS_B)}"
        victims[vid] = org
    return victims


VICTIMS = _build_victims()


def _build_customers():
    rng = random.Random(SEED + 1)
    customers = {}
    for index in range(750):
        customer_id = f"C-{rng.getrandbits(48):012x}"
        customers[customer_id] = f"{rng.choice(_WORDS_A)} {rng.choice(_WORDS_B)}"
    paid_customer = list(customers)[612]
    return customers, paid_customer


CUSTOMERS, PAID_CUSTOMER_ID = _build_customers()

PORTAL_SHELL = """
<!doctype html>
<html><head><title>{{ title }} | VoidCrypt</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#080909;color:#d8dedb;font:14px/1.5 Arial,sans-serif}.shell{max-width:980px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #303633;padding-bottom:18px}.brand{font:700 24px/1 monospace;letter-spacing:2px;color:#f0f2ef}.brand b{color:#e0473d}.tag,.eyebrow{font:12px monospace;letter-spacing:1px;color:#98a59f}.nav{display:flex;gap:18px;margin:20px 0 30px;padding:12px 0;border-bottom:1px solid #202522;font:12px monospace;color:#89948e}.nav span:first-child{color:#e0473d}.panel{background:#111413;border:1px solid #303633;padding:28px;box-shadow:0 12px 35px #0006}.eyebrow{color:#e0473d;margin:0 0 10px}h1{font-size:28px;letter-spacing:-.5px;margin:0 0 22px;color:#f4f6f4}p{max-width:680px;color:#b7c0ba}a{color:#dcece0;text-decoration-color:#e0473d;text-underline-offset:4px}code{font:12px monospace;background:#080909;border:1px solid #2d3430;padding:3px 6px}.row{display:flex;justify-content:space-between;gap:20px;padding:12px 0;border-top:1px solid #2a302d;font-family:monospace}.status{font-weight:700;letter-spacing:1px}.pending{color:#d7a945}.paid{color:#78c38a}.key{margin-top:14px;padding:13px;background:#080909;border-left:3px solid #78c38a;word-break:break-all;font-family:monospace}form{display:flex;gap:10px;align-items:end;margin:22px 0}label{display:grid;gap:6px;font:12px monospace;color:#98a59f}input{min-width:250px;padding:10px;background:#080909;color:#eef1ee;border:1px solid #3a433e;font-family:monospace}button{padding:10px 15px;background:#e0473d;color:#fff;border:0;font-weight:700;cursor:pointer}.footer{margin-top:26px;color:#6d7771;font:11px monospace}.notice{border-left:3px solid #e0473d;padding-left:13px;color:#b7c0ba}</style></head>
<body><!-- Archived service-status notices: /noticeboard --><div class="shell"><header class="top"><div class="brand">VOID<b>CRYPT</b></div><div class="tag">SECURE CLIENT CONSOLE</div></header><nav class="nav"><span>CASE STATUS</span><span>PAYMENT RECORDS</span><span>SUPPORT CHANNEL</span></nav><main class="panel"><p class="eyebrow">{{ eyebrow }}</p>{{ body|safe }}</main><footer class="footer">VOIDCRYPT CLIENT SERVICES · ALL CASE ACTIVITY IS LOGGED</footer></div></body></html>
"""


def portal_page(title, eyebrow, body):
    return render_template_string(PORTAL_SHELL, title=title, eyebrow=eyebrow, body=body)

@app.route("/")
def index():
    return portal_page("Recovery support", "CLIENT CASE MANAGEMENT", """
    <h1>Recovery support</h1><p>Your organization has been assigned a case reference. Open
    <code>/victim/&lt;your case id&gt;</code> to review its current status.</p>
    <p class=\"notice\">Lost case references cannot be recovered through this portal. Use the
    contact channel provided with your case.</p>""")


@app.route("/noticeboard")
def noticeboard():
    return portal_page("Service notices", "ARCHIVE", """<h1>Service-status notices</h1>
    <p>Payment processing is handled separately from support cases.</p>
    <p><a href=\"/payment-status\">Open payment status information</a></p>""")


@app.route("/payment-status")
def payment_status():
    return portal_page("Payment status", "RECORDS", """<h1>Payment status information</h1>
    <p>Payment status is maintained per customer profile.</p>
    <p><a href=\"/payment-records/\">Open customer directory</a></p>""")


@app.route("/payment-records/")
def payment_records():
    return portal_page("Customer directory", "PAYMENT RECORDS", """<h1>Customer directory</h1>
    <p><a href=\"customers.csv\">Download customer directory (CSV)</a></p>
    <p>Use a customer ID from the directory to view its profile.</p>
    <form onsubmit=\"location.href='/payment-records/customer/'+encodeURIComponent(this.customer_id.value); return false;\">
      <label>Customer ID <input name=\"customer_id\" required></label>
      <button type=\"submit\">View profile</button>
    </form>
    <p>Profile address format: <code>/payment-records/customer/&lt;customer id&gt;</code></p>""")


@app.route("/payment-records/customers.csv")
def customer_directory():
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["customer_id", "organization"])
    for customer_id, org in CUSTOMERS.items():
        writer.writerow([customer_id, org])
    return output.getvalue(), 200, {"Content-Type": "text/csv"}


@app.route("/payment-records/customer/<customer_id>")
def customer(customer_id):
    if customer_id not in CUSTOMERS:
        abort(404)
    if customer_id == PAID_CUSTOMER_ID:
        return portal_page("Customer profile", "CUSTOMER RECORD", f"""<h1>Customer profile</h1>
        <div class=\"row\"><span>Organization</span><span>{CUSTOMERS[customer_id]}</span></div>
        <div class=\"row\"><span>Payment status</span><span class=\"status paid\">SETTLED</span></div>
        <div class=\"row\"><span>Support case</span><code>{PAID_ID}</code></div>""")
    return portal_page("Customer profile", "CUSTOMER RECORD", f"""<h1>Customer profile</h1>
    <div class=\"row\"><span>Organization</span><span>{CUSTOMERS[customer_id]}</span></div>
    <div class=\"row\"><span>Payment status</span><span class=\"status pending\">PENDING</span></div>""")


@app.route("/victim/<vid>")
def victim(vid):
    if vid not in VICTIMS:
        abort(404)
    org = VICTIMS[vid]
    paid = vid == PAID_ID
    payment = "<span class=\"status paid\">PAID</span>" if paid else "<span class=\"status pending\">PENDING</span>"
    release = f"<p>Payment confirmed. Recovery key released:</p><div class=\"key\">{RECOVERY_KEY}</div>" if paid else "<p class=\"notice\">No payment has been recorded for this case.</p>"
    return portal_page("Case record", "CASE RECORD", f"""<h1>Case {vid}</h1>
    <div class=\"row\"><span>Organization</span><span>{org}</span></div>
    <div class=\"row\"><span>Payment status</span>{payment}</div>{release}""")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
