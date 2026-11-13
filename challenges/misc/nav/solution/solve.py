import base64
import re
from pathlib import Path
def solve():
    data=(Path(__file__).parents[1]/"dist/nav_log.txt").read_text()
    match=re.search(r"(?m)^([^\s#]+)\s+# base64$", data)
    if not match: raise ValueError("coordinate payload missing")
    return "flag{"+base64.b64decode(match.group(1),validate=True).decode()+"}"
