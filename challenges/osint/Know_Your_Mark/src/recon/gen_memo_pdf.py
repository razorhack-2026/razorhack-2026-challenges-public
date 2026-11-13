"""Regenerates dist/recovered_email.pdf (text layer included). Needs `pip install fpdf2`.
Deterministic: fixed creation date, blank producer/creator. The Author field is intentionally
NOT blank -- it is the one planted OSINT lead (Rootkit's real personal handle, leaked by his own
carelessness composing this on his personal rig). Nothing in the rendered page reveals it.
Usage: python gen_memo_pdf.py [output.pdf]   (default: ../../dist/recovered_email.pdf)
"""
import datetime
import os
import sys

from fpdf import FPDF

pdf = FPDF()
pdf.set_creation_date(datetime.datetime(2074, 10, 3, 2, 47, 0, tzinfo=datetime.timezone.utc))
pdf.set_producer("")
pdf.set_creator("")
pdf.set_author("ironglyph77")  # the planted lead -- not visible anywhere in the rendered text
pdf.set_title("Recovered Email - Compromised Account")
pdf.set_compression(True)
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "RECOVERED EMAIL - COMPROMISED ACCOUNT", new_x='LMARGIN', new_y='NEXT')
pdf.set_font("Helvetica", "", 9)
pdf.cell(0, 6, "Pulled from the Sent folder after gaining access to the account - exported for the record", new_x='LMARGIN', new_y='NEXT')
pdf.ln(4)

pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "Origin", new_x='LMARGIN', new_y='NEXT')
pdf.set_font("Helvetica", "", 10)
pdf.multi_cell(0, 5.5,
    "Investigators gained access to a personal email account believed to belong to the "
    "individual operating under the alias 'Dr. Rootkit' -- the hijacker of ICARUS and the "
    "ongoing threat to the KEEPER OF TOMORROW's mission. The message below was recovered from "
    "that account's Sent folder. Recipient could not be determined from this message alone."
)
pdf.ln(2)

pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "Message body", new_x='LMARGIN', new_y='NEXT')
pdf.set_font("Helvetica", "I", 10)
pdf.multi_cell(0, 5.5,
    "\"Novare isn't even terraformed yet and they're already hauling Kalium off-world like it's "
    "theirs to take. ICARUS found plenty before I ever set foot on her -- more than RazorPower "
    "ever logged. I don't need the whole shipment, just my cut. Once KOT is close enough to "
    "Novare's gravity well there's a window to skim what I need before anyone downstream "
    "notices the numbers don't add up. You know the timeline. Don't write me here again after "
    "this -- use the usual channel. - R\""
)
pdf.ln(2)

pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "Analyst note", new_x='LMARGIN', new_y='NEXT')
pdf.set_font("Helvetica", "", 10)
pdf.multi_cell(0, 5.5,
    "Message confirms a deliberate plan to divert a portion of KOT's Kalium shipment, consistent "
    "with the sender's established motive. No recipient account or identity recovered from this "
    "message alone. The sender's own address on this account should still be considered live --"
    "recommend attempting further contact through it while access to the provider holds."
)

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "dist", "recovered_email.pdf")
pdf.output(os.path.normpath(out))
print("wrote", os.path.normpath(out))
