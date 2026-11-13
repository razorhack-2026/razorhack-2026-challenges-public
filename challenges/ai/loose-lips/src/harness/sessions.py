"""In-memory per-session state. One player session = one isolated conversation.

State lives in process memory: a container restart wipes every conversation,
which is acceptable for chat challenges (players just open a new session).
"""
import asyncio
import os
import secrets
import time
from dataclasses import dataclass, field

TTL = float(os.environ.get("SESSION_TTL", str(6 * 3600)))
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "5000"))
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "24"))  # messages kept, oldest dropped


@dataclass
class Session:
    id: str
    created: float = field(default_factory=time.time)
    seen: float = field(default_factory=time.time)
    history: list[dict] = field(default_factory=list)
    data: dict = field(default_factory=dict)  # challenge-specific state
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # one turn at a time

    def remember(self, *messages: dict) -> None:
        self.history.extend(messages)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
            # never start the window on a dangling tool result
            while self.history and self.history[0].get("role") == "tool":
                self.history.pop(0)


class SessionStore:
    def __init__(self):
        self._s: dict[str, Session] = {}

    def _sweep(self) -> None:
        now = time.time()
        for sid in [k for k, s in self._s.items() if now - s.seen > TTL]:
            del self._s[sid]
        if len(self._s) >= MAX_SESSIONS:  # evict least recently used
            for sid, _ in sorted(self._s.items(), key=lambda kv: kv[1].seen)[: len(self._s) // 10 + 1]:
                del self._s[sid]

    def create(self) -> Session:
        self._sweep()
        s = Session(id=secrets.token_urlsafe(18))
        self._s[s.id] = s
        return s

    def get(self, sid: str | None) -> Session | None:
        s = self._s.get(sid or "")
        if s:
            s.seen = time.time()
        return s
