#!/usr/bin/env python3
"""Find the settled customer profile and its associated case reference."""
import argparse
import csv
import io
import re

import requests


def find_case_and_key(portal: str):
    homepage = requests.get(portal, timeout=10)
    homepage.raise_for_status()
    notice_match = re.search(r"Archived service-status notices:\s*(\S+)", homepage.text)
    if not notice_match:
        return None

    notice = requests.get(f"{portal}{notice_match.group(1)}", timeout=10)
    notice.raise_for_status()
    payment_match = re.search(r'href="([^"]*payment-status[^"]*)"', notice.text)
    if not payment_match:
        return None

    payment = requests.get(f"{portal}{payment_match.group(1)}", timeout=10)
    payment.raise_for_status()
    records_match = re.search(r'href="([^"]*payment-records/[^"]*)"', payment.text)
    if not records_match:
        return None

    directory = requests.get(f"{portal}{records_match.group(1)}customers.csv", timeout=10)
    directory.raise_for_status()
    for row in csv.DictReader(io.StringIO(directory.text)):
        profile = requests.get(f"{portal}/payment-records/customer/{row['customer_id']}", timeout=10)
        profile.raise_for_status()
        if "SETTLED" not in profile.text:
            continue
        case_match = re.search(r"<code>(\S+)</code>", profile.text)
        if not case_match:
            return None
        case_id = case_match.group(1)
        case_page = requests.get(f"{portal}/victim/{case_id}", timeout=10)
        case_page.raise_for_status()
        key_match = re.search(r'<div class="key">([^<]+)</div>', case_page.text)
        return (case_id, key_match.group(1).strip()) if key_match else None
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--portal", required=True, help="e.g. http://localhost:8080")
    args = parser.parse_args()
    result = find_case_and_key(args.portal.rstrip("/"))
    if not result:
        raise SystemExit("No settled customer profile found.")
    case_id, recovery_key = result
    print(f"case_id={case_id}")
    print(f"recovery_key={recovery_key}")


if __name__ == "__main__":
    main()
