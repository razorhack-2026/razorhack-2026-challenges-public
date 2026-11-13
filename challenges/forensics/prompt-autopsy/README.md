# Prompt Autopsy

**Category:** Forensics
**Difficulty:** Medium
**Author:** Andy Roid

## Description

We pulled a block of intercepted HTTPS off the enemy mining ship ICARUS — its
navigation AI (NAV-CORE) talking to its own model backend, plus a relay check-in.
Our DLP box logged the cleartext over TLS (keys attached), but the controller's
orders were never written down anywhere you can just read. Reconstruct what
NAV-CORE was actually doing from its actions, find where it phones home, and
recover what it exfiltrated about the Keeper of Tomorrow.

## Files Provided

- `session.pcap` — packet capture of NAV-CORE's outbound HTTPS
- `sslkeys.log` — TLS key log (`SSLKEYLOGFILE` format) for that capture

No network required.
