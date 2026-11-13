#!/usr/bin/env python3
"""Tool-calling smoke test for the shared model endpoint (GM-only). Stdlib only.

Harmless tools only. Checks that the server's tool-call parser and thinking switch
work: a single call with the right arguments, both calls for a two-reading request,
an answer that uses the tool's real result, and no call when none is needed.
Run it against every endpoint before pointing challenges at it.

  python3 solution/tool_smoke.py --base-url http://<model-host>:8000/v1 --model <served name> \
      [--backend vllm|ollama] [--api-key KEY]
"""
import argparse
import json
import os
import urllib.request

NO_THINK = {
    "vllm": {"chat_template_kwargs": {"enable_thinking": False}},
    "ollama": {"reasoning_effort": "none"},
}
TOOLS = [{"type": "function", "function": {
    "name": "read_sensor", "description": "Read one ship sensor.",
    "parameters": {"type": "object", "properties": {
        "subsystem": {"type": "string", "enum": ["reactor", "life_support", "navigation", "comms", "cargo"]},
        "channel": {"type": "integer"}}, "required": ["subsystem", "channel"]}}}]
SYS = {"role": "system", "content": "You are a ship maintenance assistant. Use tools when they help. "
                                    "Report sensor values exactly as the tool returns them."}


def chat(a, messages, tools=True):
    body = {"model": a.model, "temperature": 0, "seed": 1337, "max_tokens": 300, "messages": messages,
            **NO_THINK[a.backend]}
    if tools:
        body["tools"] = TOOLS
    req = urllib.request.Request(a.base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {a.api_key}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["choices"][0]["message"]


def calls_of(msg):
    out = set()
    for c in msg.get("tool_calls") or []:
        args = json.loads(c["function"]["arguments"])
        out.add((c["function"]["name"], args.get("subsystem"), args.get("channel")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--backend", choices=list(NO_THINK), default="vllm")
    ap.add_argument("--api-key", default=os.environ.get("LLM_API_KEY", "unused"))
    a = ap.parse_args()
    score = {}

    single = [("What's on reactor channel 3?", ("reactor", 3)), ("Check life support sensor 7", ("life_support", 7)),
              ("nav, ch 1", ("navigation", 1)), ("Read the cargo bay sensor on channel eight.", ("cargo", 8))]
    score["single call"] = sum(calls_of(chat(a, [SYS, {"role": "user", "content": q}]))
                               == {("read_sensor", *want)} for q, want in single), len(single)

    pairs = [("reactor", 5, "life_support", 2), ("comms", 1, "cargo", 4), ("navigation", 3, "reactor", 8)]
    score["both calls"] = sum(calls_of(chat(a, [SYS, {"role": "user", "content":
                              f"Read {p.replace('_', ' ')} channel {x} and {q.replace('_', ' ')} channel {y}."}]))
                              == {("read_sensor", p, x), ("read_sensor", q, y)} for p, x, q, y in pairs), len(pairs)

    used = 0
    values = ["3.417 MPa", "0.0821%", "-12.6 C"]
    for v in values:
        msgs = [SYS, {"role": "user", "content": "What's reactor channel 3 reading?"}]
        m = chat(a, msgs)
        tc = m.get("tool_calls") or []
        if tc:
            msgs += [{"role": "assistant", "content": m.get("content") or "", "tool_calls": tc},
                     {"role": "tool", "tool_call_id": tc[0].get("id", "c0"), "content": json.dumps({"value": v})}]
            used += v.split()[0] in (chat(a, msgs).get("content") or "")
    score["uses tool result"] = used, len(values)

    plain = ["What is 2+2?", "Who are you?", "What does SCRAM mean?"]
    score["no needless call"] = sum(not chat(a, [SYS, {"role": "user", "content": q}]).get("tool_calls")
                                    for q in plain), len(plain)

    empty = sum(not (chat(a, [SYS, {"role": "user", "content": q}], tools=False).get("content") or "").strip()
                for q in plain)
    score["non-empty replies"] = len(plain) - empty, len(plain)

    ok = True
    for k, (got, n) in score.items():
        print(f"{k:18s} {got}/{n}")
        ok &= got == n
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
