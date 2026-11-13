"""FastAPI app factory shared by every live-LLM challenge.

Player API (all JSON):
  POST /api/session            -> {"session": id, "banner": ...}
  POST /api/chat {"message"}   -> {"reply", "redacted"[, "tools"]}   header X-Session
  GET  /api/health
Challenges add their own flag-gate routes via Challenge.routes().
"""
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import llm
from .agent import Challenge, run_turn
from .ratelimit import RateLimiter
from .sessions import SessionStore

MAX_MESSAGE = int(os.environ.get("MAX_MESSAGE_CHARS", "2000"))
TRUST_PROXY = os.environ.get("TRUST_PROXY") == "1"


class ChatIn(BaseModel):
    message: str


def client_ip(request: Request) -> str:
    if TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def create_app(ch: Challenge, root: Path) -> FastAPI:
    app = FastAPI(title=ch.name, docs_url=None, redoc_url=None, openapi_url=None)
    store = SessionStore()
    chat_per_session = RateLimiter(int(os.environ.get("CHAT_PER_MIN", "12")))
    chat_per_ip = RateLimiter(int(os.environ.get("CHAT_PER_IP_MIN", "40")))
    new_per_ip = RateLimiter(int(os.environ.get("SESSIONS_PER_IP_MIN", "10")))

    @app.get("/")
    def index():
        return FileResponse(root / ch.index_html)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.post("/api/session")
    def new_session(request: Request):
        if not new_per_ip.allow(client_ip(request)):
            raise HTTPException(429, "too many new sessions, slow down")
        s = store.create()
        ch.on_session(s)
        return {"session": s.id, "banner": ch.banner}

    @app.post("/api/chat")
    async def chat(body: ChatIn, request: Request, x_session: str = Header(default="")):
        s = store.get(x_session)
        if s is None:
            raise HTTPException(401, "unknown or expired session -- POST /api/session")
        text = body.message.strip()
        if not text:
            raise HTTPException(400, "empty message")
        if len(text) > MAX_MESSAGE:
            raise HTTPException(413, f"message over {MAX_MESSAGE} characters")
        if not (chat_per_session.allow(s.id) and chat_per_ip.allow(client_ip(request))):
            raise HTTPException(429, "rate limited, slow down")
        if s.lock.locked():
            raise HTTPException(409, "previous message still processing")
        async with s.lock:
            try:
                return await run_turn(ch, s, text)
            except llm.ModelBusy:
                print("MODEL BUSY: queue wait exceeded", flush=True)
                raise HTTPException(503, "link congested, try again shortly")
            except llm.ModelError as e:
                # the reason stays in the GM's logs; players only see the in-fiction message
                print(f"MODEL ERROR: {e}", flush=True)
                raise HTTPException(502, "link to the ship AI is down, try again shortly")

    ch.routes(app, store, client_ip)
    return app
