# Changelog

## v1.2.0
- **Security:** `/admin` no longer derives operator status from the
  `X-Console-Role` request header. Those headers cross the public inspector
  proxy and are attacker-controlled, which allowed unauthenticated retrieval of
  the reactor override code. Authorization now requires a valid, server-signed
  operator session. (Reported by the internal red team.)

## v1.1.0
- Add operator admin panel: `GET /admin` (alias `/api/console/override`) returns
  the reactor master override code for authorized operators.
- Operators on the maintenance LAN are recognized via the `X-Console-Role`
  header set by the internal proxy, so bay techs don't have to log in.

## v1.0.0
- Initial MCPJam Console: operator landing page and `/health` liveness probe.
