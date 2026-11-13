# Getting Checked In — Solution

**Category:** Web
**Difficulty:** Easy
**Author:** WALL-D
**Metadata:** [../metadata/challenge1.yml](../metadata/challenge1.yml)

## Description (what the competitor sees)

See `description` in [../metadata/challenge1.yml](../metadata/challenge1.yml).

## Files Provided

None. The challenge is the hosted RASA kiosk (the Flask app in [../src/](../src/)).

## Flag

`flag{0nb0@rd!ng_th3_k33p3r_0f_t0m0rr0w}`

Source of truth: the last line of `src/templates/general_documents/Welcome.md`.

## Solution

This is the training tier: the point is to make the competitor actually use the kiosk and then read
the library it unlocks, all the way to the bottom.

1. **Check in.** On the kiosk page, use **Add New User** to register: scan (or upload) a face, then
   scan (or upload) a valid badge, and enter the name printed on it. Any badge level works for the
   General library.
2. **Log in to General.** Choose **General**. The kiosk re-scans the face (step 1: who are you) and
   the badge (step 2: is it yours — color/label agree, right level, name matches the registered
   badge). On success it prints `LOGIN SUCCESSFUL` in the server terminal and opens the General
   document library for 15 minutes.
3. **Read the documents.** The library is RASA onboarding flavor (Welcome, FAQ, How To Read,
   Connection, Safety, Cafeteria). **How To Read** explicitly tells players that important
   information hides at the bottom of documents people stop reading halfway through.
4. **Find the flag.** The last line of **Welcome to RASA**, after "here's something for your
   trouble," is the flag.

## Solve Script

None — this level is solved by hand through the web UI.

## Techniques / Tags

`misc`, `read-carefully`

## Notes

- Anyone registered at any badge level can reach the General library, so this flag has no badge
  requirement — it's purely a "did you read it" gate.
- The flag text lives in a competitor-facing document, so it is not a secret in the usual sense; it
  is meant to be found by reading.
- Deployment is shared with challenge 2 (Access Elevation) — see [../README.md](../README.md).
