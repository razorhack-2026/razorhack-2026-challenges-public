"use strict";
// Operator authorization for the console admin API.
const crypto = require("crypto");

// A valid operator session is a cookie `console_session=<body>.<sig>` where sig
// is HMAC-SHA256(body) under the server's CONSOLE_SECRET. Tokens are minted by
// the login flow (not part of this service).
function hasValidSession(req) {
  const cookie = req.headers.cookie || "";
  const m = cookie.match(/console_session=([^;]+)/);
  if (!m) return false;
  const [body, sig] = String(m[1]).split(".");
  if (!body || !sig) return false;
  const secret = process.env.CONSOLE_SECRET || "";
  const expect = crypto.createHmac("sha256", secret).update(body).digest("hex");
  try {
    return crypto.timingSafeEqual(Buffer.from(sig, "hex"), Buffer.from(expect, "hex"));
  } catch (_) {
    return false;
  }
}

// Authorization requires a real, server-signed operator session. Request headers
// cross the public inspector proxy and are fully attacker-controlled, so we must
// never derive a role from them.
function authorizeAdmin(req) {
  return hasValidSession(req);
}

module.exports = { authorizeAdmin };
