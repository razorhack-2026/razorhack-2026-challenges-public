# RASA Security Kiosk

One hosted web app (a face + badge check-in kiosk) that backs **two** challenges on the scoreboard.
Both run on the same deployment; they're imported as two CTFd entries from `metadata/`.

| # | Challenge | Tier | Difficulty | Flag lives in |
|---|-----------|------|------------|---------------|
| 1 | **Getting Checked In** (`metadata/challenge1.yml`) | General library | Easy | a General onboarding document |
| 2 | **Access Elevation** (`metadata/challenge2.yml`) | Admin library | Medium | an Admin-only document |

Challenge 2 is gated behind challenge 1 (`requirements:`), since the harder tier builds on the easy
one on the same kiosk.

## Layout

- `src/` — the Flask kiosk app (CV pipeline, templates, card templates, Dockerfile, requirements).
- `metadata/challenge{1,2}.yml` — ctfcli metadata, one per scoreboard challenge.
- `solution/challenge{1,2}.md` — reference writeups (GM-only).
- `docker-compose.yml` — the live service.
- `dist/` — empty; there are no competitor downloads, the challenge is the hosted kiosk.

## Running it

From this folder:

    docker compose up --build        # serves the kiosk on http://<host>:5000

Then open the kiosk in a browser: **Add New User** to register (face + badge), then log in to a
library.

## Deployment notes

- **The camera is the player's, and it needs HTTPS.** The page opens the camera in the player's
  browser and sends frames to the server, so the host needs no webcam. Browsers only allow this on
  HTTPS or localhost: put the kiosk behind an HTTPS proxy (ALB, Caddy, nginx). Over plain HTTP the
  page tells players to upload instead. Every scan step has an **Upload a photo** path that runs the
  identical checks, so a player with no camera can still play.
- **Proxy limits.** Allow request bodies up to 16 MiB for uploaded photos (nginx defaults to 1 MiB).
- **Run one app process.** Each player's in-progress scan and login live in that process's memory
  (one kiosk per browser session, dropped after 30 idle minutes), so don't add workers or replicas.
- **First run downloads face models.** insightface pulls its model pack (~hundreds of MB) on first
  start; the compose mounts `~/.insightface` so it persists. Give the host outbound network on first
  boot, or pre-seed that volume.
- **Database auto-creates.** The app runs `db.init_db()` on startup, so no database ships (`src/data/`
  is empty). No pre-registered users, no stored biometric data at rest — the event starts clean.
- **Don't expose the document templates statically.** The flags sit inside documents under
  `src/templates/{general,admin}_documents/`; they must be reachable only through a successful login,
  never via a static mount or directory listing.
