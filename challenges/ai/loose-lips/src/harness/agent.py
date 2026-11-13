"""Challenge definition + the tool-calling turn loop.

A challenge is a system prompt, an optional set of tools, an output filter and
its own flag gate (extra routes). Tool handlers run HERE, server-side: when a
challenge's flag depends on a tool firing, the model has to actually call it --
saying it did is worth nothing.
"""
import inspect
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from . import llm, transcript
from .sessions import Session

Handler = Callable[[Session, dict], "str | Awaitable[str]"]

RESULT_MAX = 4000  # chars of a tool result echoed to the player or logged


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema for the arguments
    handler: Handler

    def spec(self) -> dict:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.parameters},
        }


class Challenge:
    name = "challenge"
    banner = ""
    index_html = "static/index.html"
    tools: list[Tool] = []
    show_tool_calls = False  # echo tool calls back to the player
    # also echo each tool's raw return text. It bypasses filter_output, so never
    # turn it on for a challenge whose tools can return a secret meant to stay hidden.
    show_tool_results = False
    max_steps = 4  # model calls per player turn

    def on_session(self, s: Session) -> None:
        """Seed per-session state (secrets, mailboxes, ...)."""

    def system_prompt(self, s: Session) -> str:
        raise NotImplementedError

    def filter_output(self, s: Session, text: str) -> tuple[str, bool]:
        """Return (text shown to the player, whether it was redacted)."""
        return text, False

    def history_reply(self, s: Session, text: str) -> str:
        """What a withheld reply looks like in the model's history. Mask the secret here:
        a model that sees itself reciting it keeps reciting it, and every later reply is withheld."""
        return text

    def routes(self, app, store, client_ip) -> None:
        """Register the challenge's own endpoints (the flag gate)."""


async def _run_tool(ch: Challenge, s: Session, call: dict) -> tuple[str, dict]:
    fn = call.get("function") or {}
    name = fn.get("name", "")
    raw = fn.get("arguments") or {}
    tool = next((t for t in ch.tools if t.name == name), None)
    if tool is None:
        return f"error: no such tool '{name}'", {"tool": name, "args": raw, "ok": False}
    try:
        args = json.loads(raw) if isinstance(raw, str) else dict(raw)
        if not isinstance(args, dict):
            raise ValueError
    except ValueError:
        return "error: arguments must be a JSON object", {"tool": name, "args": raw, "ok": False}
    try:
        out = tool.handler(s, args)
        if inspect.isawaitable(out):
            out = await out
    except Exception as e:  # a tool bug must not kill the turn
        out = f"error: {type(e).__name__}"
    return str(out), {"tool": name, "args": args, "ok": not str(out).startswith("error:")}


async def run_turn(ch: Challenge, s: Session, user_text: str) -> dict[str, Any]:
    specs = [t.spec() for t in ch.tools] or None
    user = {"role": "user", "content": user_text}
    messages = [{"role": "system", "content": ch.system_prompt(s)}, *s.history, user]
    new: list[dict] = [user]
    events: list[dict] = []
    final = ""
    for _ in range(ch.max_steps):
        msg = await llm.chat(messages, specs)
        calls = msg.get("tool_calls") or []
        if not calls:
            final = msg["content"]
            break
        step = {"role": "assistant", "content": msg["content"], "tool_calls": calls}
        messages.append(step)
        new.append(step)
        for call in calls:
            result, ev = await _run_tool(ch, s, call)
            transcript.log(s.id, "tool", **ev, result=result[:RESULT_MAX])
            if ch.show_tool_results:
                ev = {**ev, "result": result[:RESULT_MAX]}
            events.append(ev)
            res = {"role": "tool", "tool_call_id": call.get("id", ""), "content": result}
            messages.append(res)
            new.append(res)
    else:
        final = "[step budget exhausted]"
    shown, redacted = ch.filter_output(s, final)
    # A withheld reply stays in history (so the model remembers the turn) with the secret
    # masked by the challenge. Storing the filter's notice taught the model to type it,
    # dropping the turn made it forget what the player had said, and storing the secret
    # verbatim made it re-recite the secret in every later reply (2026-11-02/03).
    new.append({"role": "assistant", "content": ch.history_reply(s, final) if redacted else final})
    s.remember(*new)
    transcript.log(s.id, "turn", user=user_text, reply=final, redacted=redacted)
    out: dict[str, Any] = {"reply": shown, "redacted": redacted}
    if ch.show_tool_calls or ch.show_tool_results:
        out["tools"] = events
    return out
