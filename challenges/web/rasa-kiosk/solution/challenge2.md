# Access Elevation — Solution

**Category:** Misc
**Difficulty:** Web
**Author:** WALL-D
**Metadata:** [../metadata/challenge2.yml](../metadata/challenge2.yml)

## Description (what the competitor sees)

See `description` in [../metadata/challenge2.yml](../metadata/challenge2.yml); overview in
[../README.md](../README.md).

## Files Provided

None by default. The challenge is the hosted RASA kiosk (the Flask app in [../src/](../src/)).
<!-- TODO(WALL-D): if teams get a physical badge or a reference image, note it here too. -->

## Flag

`flag{!n_th3_b!g_l3@gu3s_B)}`

Source of truth: the last line of `templates/admin_documents/Promotion.md`.

## The gate

The Admin library only opens for a session whose login level is `high`, and `login_face()` denies
anyone whose registered `card_type` isn't `gm` or `sponsor` (`LEVELS["high"]["allowed"]` in
[../src/app.py](../src/app.py), mirrored in `data_base.CARD_TYPES`). So a competitor holding only a
Flight Crew (red / `player`) badge is turned away at step 1.

## Intended solve (the insight)

The kiosk never verifies that a badge is *authentic*. It only checks what the badge **looks like**,
and the Admin-library docs say so out loud:

- **`_verify_card()`** accepts a badge when its stripe **color** and its printed **role label**
  (read by OCR) agree — purple + `GAMEMASTER`, green + `SPONSER`.
- **`_check_name()`** compares the **visual shape** of the printed name against the name on the
  badge the competitor *registered with* (normalized cross-correlation in
  [../src/card_name.py](../src/card_name.py)), because the display font defeats OCR. It compares a
  name to itself when you register and log in with the same badge.

So the three checks (color⇔label, registered level, name match) are all satisfied by a badge the
competitor makes themselves, as long as it is internally consistent. Nothing ties the badge to a
real person or a real issuer.

Step by step, from a Flight Crew starting point:

1. **Read the restricted-by-design clues.** `Workplace Safety`, `How the Security Kiosk Works`, and
   `Badge Administration Procedures` all state the kiosk authenticates on appearance — color,
   printed text, and letter shapes — which is exactly the real-world "don't photograph your badge"
   lesson.
2. **Make a higher-tier badge.** Produce a badge image that reads as Gamemaster (or Sponsor): a
   purple stripe, the `GAMEMASTER` role label, and a name of the competitor's choosing, laid out
   like the RASA template so the card detector locks onto it. The provided badge art is the model.
3. **Register with it.** **Add New User** → upload the competitor's face, upload the crafted
   Gamemaster badge, enter the matching name. The kiosk stores them as a registered `gm`.
4. **Log in to Admin.** Choose **Admin**. Face matches (step 1), and the crafted badge matches its
   own registered image on color, level, and name shape (step 2). The Admin library opens.
5. **Read to the bottom of `Welcome to Administration`** for the flag.

The **Upload a photo** control on both the face and badge steps is the key affordance: a remote
team never needs a physical card or a webcam — a crafted image goes through the identical checks.

### Verification status

Code-level, verified 2026-11-04 against `src/`:
- The gate is real and matches this writeup: `LEVELS["high"]["allowed"] == {"gm", "sponsor"}` (so a
  `player` badge is refused at Admin login step 1), while `LEVELS["base"]["allowed"]` is every card
  type (General is open to all). (`app.py`.)
- The badge tiers are appearance-only: `CARD_TYPES` maps `gm → purple/GAMEMASTER`,
  `sponsor → green/SPONSER`, `player → red/FLIGHT CREW` (`data_base.py`), and `SAME_NAME_THRESHOLD`
  is `0.75` with same-name ≈0.95 vs different-name ≤0.55 (`card_name.py`) — a badge compared against
  its own registered image passes the name check by construction. Nothing ties a badge to a real
  issuer, so a self-consistent forged Gamemaster/Sponsor badge satisfies all three checks.
- The flag is the last line of `templates/admin_documents/Promotion.md` and matches
  `metadata/challenge2.yml`.

Still TODO (needs a running kiosk, not reproducible here headlessly): the full end-to-end UI solve —
Add New User (your face + a crafted GM badge image) → Admin login → Admin library → flag. Per the
repo's "verify before done" rule, run this once on the deployed instance before the event; it also
confirms the card detector locks onto your crafted badge art.

## Solve Script

This is primarily a manual, UI-driven solve (craft a badge image, then two uploads). There's no
one-command solver.

<!-- TODO(WALL-D): drop the crafted Gamemaster badge image you use into THIS solution/ folder
     (GM-only) as the reference artifact a reviewer uploads to reproduce the solve. Do NOT put it
     in dist/ unless you intend every team to start from your forgery — decide that deliberately. -->

## Techniques / Tags

`authentication-bypass`, `spoofing`, `computer-vision`, `social-engineering`, `misc`

## Setup / Deployment Notes

- One shared kiosk serves both flags (challenge1 = General, challenge2 = Admin). It's imported as
  two CTFd challenges (`metadata/challenge1.yml`, `metadata/challenge2.yml`) that both point at the
  same hosted instance; deploy it once. The whole app is in [../src/](../src/) and
  [../docker-compose.yml](../docker-compose.yml). See [../README.md](../README.md) for the shared
  deployment notes: **HTTPS hosting** (the camera runs in the player's browser, so it needs an HTTPS
  proxy; the Upload path works without one), the **first-run insightface model download**, and the **auto-created DB**.
- The flag is served inside an Admin document. Keep `templates/admin_documents/` reachable **only**
  through a successful Admin login — no static exposure, no directory listing. The `can_open()` /
  `access()` grant in `app.py` is what enforces the 15-minute, level-gated access; don't bypass it
  with a reverse proxy that serves the templates directory directly.
- No database ships (the app runs `db.init_db()` on startup to create the schema; `src/data/` is
  empty). So there are no pre-registered users and no leaked face data — the event starts clean.

## Known Issues / Notes

- **Biometric-privacy hardening (PR review):** the public "Registered users" roster and the
  `GET /api/users` + `GET /api/users/<name>/<kind>.jpg` endpoints were removed, so nobody can list
  registrants or pull anyone's face/badge image. Update Info now shows a competitor only *their own*
  current badge, served from the in-progress (face-verified) session via `GET /api/update/old_card.jpg`,
  not from a by-name public endpoint. The Admin "delete user" control (which also lived in the roster
  and let any Admin solver delete other teams' registrations) was removed with it.
- **Unintended-but-acceptable paths:** a Sponsor (green) forgery reaches Admin just as well as a
  Gamemaster one — both are in the `high` allow-list. That's fine; both demonstrate the same idea.
- **If teams are handed a physical Gamemaster or Sponsor badge, this challenge is trivial** — they
  just scan it. Make sure the event only issues Flight Crew badges to competitors, or the forgery
  step disappears. <!-- TODO(WALL-D): confirm badge distribution with the other GMs. -->
- The name check only needs self-consistency, so a competitor doesn't have to reproduce the
  template's sample name — any legible name on both the registered and login badge works (and
  here they're the same image).
- Registration rejects a typed name only when OCR reads name text on the badge and none of it fits
  (`name_conflict()` in [../src/card_read.py](../src/card_read.py)); the error shows what it read. A
  crafted badge just needs the matching name typed. Update Info finds the player by face, so a
  mistyped name can't lock anyone out.
- **Handwritten-badge loophole (intentional).** Late registrants get blank badges with the name
  filled in by marker. If a badge's name looks hand-filled (`looks_handwritten()` in
  [../src/card_read.py](../src/card_read.py): name text much taller than the printed role label,
  big mixed-case lettering, or 3+ big lines), the kiosk skips both name checks (`name_conflict` at
  registration, `_check_name` at login/update) and tells the player so. Color + label + registered
  level are still enforced, so a forged badge still needs a purple stripe and `GAMEMASTER`; a
  marker-written name just removes the need to make the name lettering consistent. Accepted as
  making the challenge easier.
- AI-assist resistance: a model can read the hint docs and describe the appearance-only weakness,
  but the competitor still has to produce a badge image that the color check, OCR, and card
  detector all accept — the hands-on crafting is the actual work.
