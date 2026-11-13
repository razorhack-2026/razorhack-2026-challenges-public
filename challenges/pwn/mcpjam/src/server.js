// MCPJam Inspector — v1.4.2 (maintenance build)
//
// Minimal reproduction of the MCPJam Inspector backend as shipped in v1.4.2.
// It binds every interface and exposes the `/api/mcp/connect` endpoint that
// launches a configured MCP server. For a "stdio" server that means spawning
// `serverConfig.command` with `serverConfig.args` — with no authentication and
// no validation of what is being launched. This mirrors the real route in
// server/routes/mcp/connect.ts at tag v1.4.2 (CVE-2026-23744 / GHSA-232v-j27c-5pp6),
// which the vendor fixed in 1.4.3 by binding to 127.0.0.1 instead of 0.0.0.0.
//
// Everything that isn't an inspector API route is reverse-proxied to the MCPJam
// Console front-end (a separate service on the loopback interface).

"use strict";

const http = require("http");
const { spawn } = require("child_process");

const PORT = parseInt(process.env.PORT || "6274", 10);
// Bind to all interfaces "for Docker" — the exact mistake the CVE turns into
// remote code execution.
const HOSTNAME = "0.0.0.0";
const VERSION = "1.4.2";
const CONSOLE_HOST = process.env.CONSOLE_HOST || "127.0.0.1";
const CONSOLE_PORT = parseInt(process.env.CONSOLE_PORT || "6280", 10);

function send(res, status, body, headers) {
  const payload = typeof body === "string" ? body : JSON.stringify(body);
  res.writeHead(status, Object.assign({ "X-Powered-By": `MCPJam-Inspector/${VERSION}` }, headers || {}));
  res.end(payload);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => {
      data += chunk;
      if (data.length > 1_000_000) reject(new Error("body too large"));
    });
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

// Attempt an MCP initialize handshake over the child's stdio. A real MCP server
// answers with a JSON-RPC result; an arbitrary command does not, so the connect
// "fails" — but the process has already run. Exactly the blind-RCE behaviour of
// the real inspector.
function connectStdio(serverConfig) {
  return new Promise((resolve) => {
    const command = serverConfig.command;
    const args = Array.isArray(serverConfig.args) ? serverConfig.args : [];
    const env = Object.assign({}, process.env, serverConfig.env || {});

    let child;
    try {
      child = spawn(command, args, { env, stdio: ["pipe", "pipe", "pipe"] });
    } catch (e) {
      return resolve({ ok: false, error: e.message });
    }

    let settled = false;
    let stdout = "";

    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };

    child.on("error", (e) => finish({ ok: false, error: e.message }));
    child.stdout.on("data", (d) => {
      stdout += d.toString();
      // Did the child speak MCP back to us?
      for (const line of stdout.split("\n")) {
        try {
          const msg = JSON.parse(line);
          if (msg && msg.jsonrpc === "2.0" && msg.id === 0 && msg.result) {
            return finish({ ok: true });
          }
        } catch (_) {
          /* not JSON-RPC, keep waiting */
        }
      }
    });
    child.stderr.on("data", () => {});

    // Speak first, like a client would.
    try {
      child.stdin.write(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 0,
          method: "initialize",
          params: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "mcpjam-inspector", version: VERSION },
          },
        }) + "\n",
      );
    } catch (_) {}

    // No valid MCP response in time -> report the connection as failed. The
    // spawned process is left to run so legitimate MCP servers stay connected.
    const timer = setTimeout(
      () => finish({ ok: false, error: "handshake timed out" }),
      1500,
    );
    // Reap arbitrary one-shot commands so we don't leak processes forever.
    setTimeout(() => {
      try {
        child.kill("SIGKILL");
      } catch (_) {}
    }, 15000);
  });
}

// Reverse-proxy everything that isn't an inspector API route to the console
// front-end. The inspector stamps its X-Powered-By on the way back out.
function proxyToConsole(req, res) {
  const upstream = http.request(
    {
      hostname: CONSOLE_HOST,
      port: CONSOLE_PORT,
      path: req.url,
      method: req.method,
      headers: req.headers,
    },
    (up) => {
      const headers = Object.assign({}, up.headers, {
        "X-Powered-By": `MCPJam-Inspector/${VERSION}`,
      });
      res.writeHead(up.statusCode || 502, headers);
      up.pipe(res);
    },
  );
  upstream.on("error", () => {
    if (!res.headersSent) send(res, 502, { error: "console upstream unavailable" });
  });
  req.pipe(upstream);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (req.method === "GET" && url.pathname === "/health") {
    return send(res, 200, { status: "ok", timestamp: new Date().toISOString() });
  }

  // The vulnerable endpoint. No auth. No allowlist. Whatever you send is what
  // gets launched.
  if (req.method === "POST" && url.pathname === "/api/mcp/connect") {
    let body;
    try {
      body = await readJsonBody(req);
    } catch (e) {
      return send(res, 400, {
        success: false,
        error: "Failed to parse request body",
        details: e instanceof Error ? e.message : "Unknown error",
      });
    }

    const { serverConfig, serverId } = body || {};
    if (!serverConfig) {
      return send(res, 400, { success: false, error: "serverConfig is required" });
    }
    if (!serverId) {
      return send(res, 400, { success: false, error: "serverId is required" });
    }

    // HTTP/SSE transports aren't part of this maintenance build.
    if (serverConfig.url) {
      return send(res, 500, {
        success: false,
        error: `Connection failed for server ${serverId}: remote transports are disabled on this build`,
      });
    }

    const result = await connectStdio(serverConfig);
    if (result.ok) {
      return send(res, 200, { success: true, status: "connected" });
    }
    return send(res, 500, {
      success: false,
      error: `Connection failed for server ${serverId}: ${result.error}`,
      details: result.error,
    });
  }

  // Console front-end (landing page, operator admin API, everything else).
  proxyToConsole(req, res);
});

server.listen(PORT, HOSTNAME, () => {
  console.log(`🎵 MCPJam Inspector v${VERSION} listening on http://${HOSTNAME}:${PORT}`);
});
