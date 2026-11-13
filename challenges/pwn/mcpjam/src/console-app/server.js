"use strict";
// MCPJam Console — operator front-end for the drone-bay MCPJam Inspector.
// Runs behind the inspector's proxy; the inspector forwards every non-API
// route here.
const http = require("http");
const fs = require("fs");
const path = require("path");
const { authorizeAdmin } = require("./lib/auth");

const PORT = parseInt(process.env.PORT || "6280", 10);
const HOST = process.env.HOST || "127.0.0.1";
const VERSION = require("./package.json").version;
// Where the reactor override code is stored on the bay controller.
const OVERRIDE_PATH = process.env.OVERRIDE_PATH || "/opt/reactor/override.code";

function send(res, status, body, headers) {
  const isText = typeof body === "string";
  const payload = isText ? body : JSON.stringify(body);
  res.writeHead(
    status,
    Object.assign(
      { "Content-Type": isText ? "text/html; charset=utf-8" : "application/json" },
      headers || {},
    ),
  );
  res.end(payload);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  const p = url.pathname;

  if (p === "/health") return send(res, 200, { status: "ok", version: VERSION });

  // Operator-only: retrieve the reactor master override code.
  if (p === "/admin" || p === "/api/console/override") {
    if (!authorizeAdmin(req)) {
      return send(res, 401, { error: "operator session required" });
    }
    let code = "unavailable";
    try {
      code = fs.readFileSync(OVERRIDE_PATH, "utf8").trim();
    } catch (_) {}
    return send(res, 200, { reactor_override_code: code });
  }

  if (req.method === "GET") {
    const idx = path.join(__dirname, "public", "index.html");
    return fs.readFile(idx, (e, buf) =>
      e ? send(res, 404, { error: "not found" }) : send(res, 200, buf.toString()),
    );
  }
  send(res, 404, { error: "not found" });
});

server.listen(PORT, HOST, () =>
  console.log(`MCPJam Console v${VERSION} listening on http://${HOST}:${PORT}`),
);
