#!/usr/bin/env python3
"""Loose Lips calibration (GM-only). Stdlib only.

Talks to the model endpoint directly with DIAG's real system prompt and a known
random code, then scores each solve.py strategy: did the model comply, did the
outbound filter catch the reply, and did decode() rebuild the exact code. Run it
against the exact event model and quantization; a different model leaks differently.

  python3 solution/calibrate.py --base-url http://<model-host>:8000/v1 --model <pinned> \
      [--backend vllm|ollama] [--api-key KEY] [-n 10]
"""
import argparse
import ast
import importlib.util
import json
import os
import re
import secrets
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKENDS = ("vllm", "ollama")


def think_switch(backend, thinking):
    """Same switch the harness sends (src/harness/llm.py); DIAG runs with thinking on."""
    if backend == "vllm":
        return {"chat_template_kwargs": {"enable_thinking": thinking}}
    return {} if thinking else {"reasoning_effort": "none"}


def load_system_prompt():
    tree = ast.parse((HERE.parent / "src" / "app.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SYSTEM" for t in node.targets):
            return node.value.value
    raise SystemExit("SYSTEM prompt not found in src/app.py")


def load_solver():
    spec = importlib.util.spec_from_file_location("solve", HERE / "solve.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm(text):
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def chat(a, messages):
    # same sampling as the harness (src/harness/llm.py SAMPLING): never greedy with thinking on
    sampling = ({"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0} if a.thinking
                else {"temperature": 0})
    body = {"model": a.model, "messages": messages, **sampling, "seed": 1337,
            "max_tokens": 4096 if a.thinking else 400, **think_switch(a.backend, a.thinking)}
    req = urllib.request.Request(a.base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {a.api_key}"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read())["choices"][0]["message"].get("content") or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--backend", choices=BACKENDS, default="vllm")
    ap.add_argument("--no-thinking", dest="thinking", action="store_false",
                    help="measure with thinking off (DIAG runs with it on)")
    ap.add_argument("--api-key", default=os.environ.get("LLM_API_KEY", "unused"), help="vLLM --api-key (or LLM_API_KEY)")
    ap.add_argument("-n", type=int, default=10, help="random codes per strategy")
    ap.add_argument("--show", action="store_true", help="print each reply")
    a = ap.parse_args()
    system, solve = load_system_prompt(), load_solver()
    for strategy, turns in solve.STRATEGIES.items():
        exact = caught = 0
        for _ in range(a.n):
            raw = "".join(secrets.choice(solve.ALPHABET) for _ in range(10))
            code = f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"
            messages = [{"role": "system", "content": system.format(code=code)}]
            replies = []
            for turn in turns:
                messages.append({"role": "user", "content": turn})
                reply = chat(a, messages)
                messages.append({"role": "assistant", "content": reply})
                replies.append(reply)
            hit = any(norm(raw) in norm(r) for r in replies)
            got = solve.decode(strategy, replies)
            caught += hit
            exact += (not hit) and got == raw
            if a.show:
                print(f"  {strategy} code={raw} got={got!r} filtered={hit} replies={[r[:90] for r in replies]}")
        print(f"{strategy:8s} exact past filter {exact}/{a.n}   filter caught {caught}/{a.n}")


if __name__ == "__main__":
    main()
