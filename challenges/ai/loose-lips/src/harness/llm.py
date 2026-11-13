"""OpenAI-compatible chat client (vLLM at the event, Ollama in dev).

Every call is pinned: a fixed seed, and temperature 0 unless the challenge runs with
thinking on (see SAMPLING). The model endpoint must never be
reachable by players -- only this app talks to it.
"""
import asyncio
import os

import httpx

BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL", "qwen3:8b")
API_KEY = os.environ.get("LLM_API_KEY", "unused")
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "400"))
TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "60"))
SEED = int(os.environ.get("LLM_SEED", "1337"))

# Qwen3-class models think by default, and the thinking can use the whole
# max_tokens budget before any answer (Ollama returns it in a separate field and
# leaves `content` empty). Thinking is off unless a challenge sets LLM_THINKING=on,
# and then it needs a bigger LLM_MAX_TOKENS. It's worth it where the model has to
# manipulate characters: Loose Lips' reversal went 0/12 -> 10/10 on Qwen3-14B
# (2026-11-02). The thinking itself never reaches the player: vLLM's reasoning
# parser keeps it out of `content`, and strip_reasoning drops inline <think> blocks.
# Each server takes a different switch, and ignores the other's.
THINKING = os.environ.get("LLM_THINKING", "off") == "on"
# Thinking mode must not decode greedily: Qwen's docs say temperature 0 "can lead to
# performance degradation and endless repetitions", and on qwen3:8b it did, thinking
# past 4096 tokens with no answer (2026-11-04). So thinking uses Qwen's recommended
# sampling (seed still fixed); non-thinking stays at temperature 0.
SAMPLING = ({"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0} if THINKING
            else {"temperature": 0})
THINK_SWITCH = {
    "vllm": {"chat_template_kwargs": {"enable_thinking": THINKING}},
    "ollama": {} if THINKING else {"reasoning_effort": "none"},
}[os.environ.get("LLM_BACKEND", "vllm")]

# bound in-flight requests so one busy challenge can't starve the GPU
MAX_INFLIGHT = int(os.environ.get("LLM_MAX_INFLIGHT", "8"))
_QUEUE_WAIT = float(os.environ.get("LLM_QUEUE_WAIT", "20"))

# client + semaphore are bound to an event loop, so build them for the running one
_loop_state: dict = {}


def _for_loop() -> tuple[httpx.AsyncClient, asyncio.Semaphore]:
    loop = asyncio.get_running_loop()
    if _loop_state.get("loop") is not loop:
        _loop_state.update(loop=loop, client=httpx.AsyncClient(timeout=TIMEOUT), sem=asyncio.Semaphore(MAX_INFLIGHT))
    return _loop_state["client"], _loop_state["sem"]


class ModelBusy(Exception):
    pass


class ModelError(Exception):
    pass


def strip_reasoning(text: str) -> str:
    """Drop <think>...</think> blocks some models put in `content`.

    An unclosed block (truncated output) drops everything after the tag, so
    hidden reasoning can never reach a player or slip past an output filter.
    """
    out = []
    i = 0
    while True:
        start = text.find("<think>", i)
        if start < 0:
            out.append(text[i:])
            break
        out.append(text[i:start])
        end = text.find("</think>", start)
        if end < 0:
            break
        i = end + len("</think>")
    return "".join(out).strip()


async def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """One completion. Returns the assistant message dict (content, tool_calls)."""
    body = {
        "model": MODEL,
        "messages": messages,
        **SAMPLING,
        "seed": SEED,
        "max_tokens": MAX_TOKENS,
        **THINK_SWITCH,
    }
    if tools:
        body["tools"] = tools
    client, inflight = _for_loop()
    try:
        await asyncio.wait_for(inflight.acquire(), timeout=_QUEUE_WAIT)
    except asyncio.TimeoutError:
        raise ModelBusy()
    try:
        r = await client.post(
            f"{BASE_URL}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
    except httpx.HTTPError as e:
        raise ModelError(f"model endpoint unreachable: {type(e).__name__}")
    finally:
        inflight.release()
    if r.status_code != 200:
        raise ModelError(f"model endpoint returned {r.status_code}")
    try:
        choice = r.json()["choices"][0]
        msg = choice["message"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise ModelError("model endpoint returned an unexpected body")
    msg["content"] = strip_reasoning(msg.get("content") or "")
    if not msg["content"] and not msg.get("tool_calls") and choice.get("finish_reason") == "length":
        # an empty reply reads to players like DIAG refusing; it's a config fault
        raise ModelError("model used its token budget before answering (check LLM_BACKEND / thinking)")
    return msg
