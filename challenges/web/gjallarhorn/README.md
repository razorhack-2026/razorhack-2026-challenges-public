# The Gjallarhorn

**Category:** Web  **Difficulty:** Hard

## Description
Woah, so you're telling me somebody made this AI defense network almost a century
ago? And it signaling for help from us, the IT department? Huh... It sounds like just a
computer virus to me, and in my professional Information Technology opinion, it seems
like whoever made this whole thing should've included some Bitdefender. Rookies, am I
right? Well anyway, if Surtr came from the Icarus, Dr. Rookit has got to be behind this,
I just know it. Here's the channel Heimdall opened to us, it looks like the console to
some space weapon called the Gjallarhorn (I'm starting to see a pattern here). It looks
like its time we become the antivirus.

## Deploy Notes
Make sure to set the `TRUST_PROXY` env var correctly based on the infra setup.  See the docker compose.
If the container is directly exposed, set to 0.  If its behind a single reverse proxy or load balancer,
set to 1, etc.