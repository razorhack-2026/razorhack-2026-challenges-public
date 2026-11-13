"""
Document libraries shown after a successful General or Admin login.

Each library is a folder of .md and .html files under templates/. Markdown is
converted to HTML; HTML files are used as-is (for a full page, only what's
inside <body> is kept, so the site's own dark theme applies). Either way the
result is shown inside the site layout (templates/doc_view.html).

Files are trusted content written by staff - raw HTML in them is not sanitized.
"""

import html
import os
import re

import markdown
from markupsafe import Markup

LIBRARIES = {
    # url slug -> login level (see LEVELS in app.py) and folder under templates/
    "general": {"level": "base", "name": "General", "dir": "general_documents"},
    "admin": {"level": "high", "name": "Admin", "dir": "admin_documents"},
}
EXTENSIONS = (".md", ".html")


def _title_from_filename(filename):
    stem = os.path.splitext(filename)[0]
    return re.sub(r"[_\-]+", " ", stem).strip().title() or filename


def _strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _title(filename, text):
    """First heading (or the HTML <title>), else a tidied-up filename."""
    if filename.endswith(".md"):
        m = re.search(r"^#\s+(.+?)\s*#*\s*$", text, re.MULTILINE)
        if m:
            return m.group(1)
    else:
        m = (re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
             or re.search(r"<h1[^>]*>(.*?)</h1>", text, re.I | re.S))
        if m and _strip_tags(m.group(1)):
            return _strip_tags(m.group(1))
    return _title_from_filename(filename)


def _read(folder, filename):
    with open(os.path.join(folder, filename), encoding="utf-8") as f:
        return f.read()


def list_documents(folder):
    """[{"file", "title", "kind"}] for every .md/.html file in `folder`, sorted by title."""
    if not os.path.isdir(folder):
        return []
    docs = []
    for name in os.listdir(folder):
        if name.startswith(".") or not name.lower().endswith(EXTENSIONS):
            continue
        if not os.path.isfile(os.path.join(folder, name)):
            continue
        docs.append({"file": name, "title": _title(name, _read(folder, name)),
                     "kind": os.path.splitext(name)[1][1:].upper()})
    return sorted(docs, key=lambda d: d["title"].lower())


def load_document(folder, filename):
    """{"file", "title", "kind", "body": Markup} for one document, or None if it isn't in the folder."""
    # Only names that list_documents() would return - no paths, no other file types.
    doc = next((d for d in list_documents(folder) if d["file"] == filename), None)
    if doc is None:
        return None
    text = _read(folder, filename)
    if filename.lower().endswith(".md"):
        body = markdown.markdown(text, extensions=["extra", "sane_lists"])
    else:
        m = re.search(r"<body[^>]*>(.*)</body>", text, re.I | re.S)
        body = m.group(1) if m else re.sub(r"<head[^>]*>.*?</head>", "", text, flags=re.I | re.S)
    body = body.replace("<table", '<div class="table-wrap"><table').replace("</table>", "</table></div>")
    return {**doc, "body": Markup(body.strip())}
