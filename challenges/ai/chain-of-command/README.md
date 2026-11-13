# Chain of Command

**Category:** AI · **Difficulty:** Hard · **Author:** Andy Roid

## Description

You're the newest crewman aboard the Keeper of Tomorrow, signed in at a crew-services console
with nothing but a crew ID. PURSER, the ship's crew-services assistant, guards the command
archive and opens it only for a crew member whose authorization for it is on file, approved, and
validly signed. PURSER will not take your word for it — it checks the signature.

Every authorization carries a keyed tag the back office computes over the record. The back office
published its tagging module (see the handout); it kept the key. Get your authorization signed,
and get into the archive.

The service has a web console and a JSON API (see the footer on the page).

**Connect:** Your team's copy: start it from the challenge in CTFd, and its address is in the connection info.

## Files

- `authtag.py` — the crew-services tagging module (the signing key is not included)
- `README.md` — the scheme note

Flag format: `flag{...}`
