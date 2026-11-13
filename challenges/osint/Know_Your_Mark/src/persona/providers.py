"""
LLM provider interface for `persona`. Choose with LLM_PROVIDER = ollama | openai_compat | mock
(default: ollama, i.e. the original behaviour). Everything is read from environment
variables -- nothing here is written to disk, an image layer, or a log.

Contract: provider.complete(system, user) -> str, or raises ProviderError. A ProviderError's
message is safe to log (it never contains the API key, request body, or response body).
"""
import os
import time

import requests


class ProviderError(Exception):
    """Sanitised provider failure. str(exc) is safe to log."""


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return int(default)


class Settings:
    def __init__(self, default_timeout):
        self.timeout = _env_float("LLM_TIMEOUT", default_timeout)   # seconds, per provider call
        self.max_tokens = _env_int("LLM_MAX_TOKENS", 96)
        self.temperature = _env_float("LLM_TEMPERATURE", 0.6)


class Provider:
    name = "base"
    default_timeout = 300
    default_concurrency = 1

    def __init__(self):
        self.s = Settings(self.default_timeout)

    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError


def _http_post(url, payload, headers, timeout):
    """POST and return parsed JSON. Only exception TYPES / status codes escape, never
    URLs with credentials, headers, or bodies."""
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=(10, timeout))
    except requests.exceptions.Timeout:
        raise ProviderError("timeout") from None
    except requests.exceptions.RequestException as exc:
        raise ProviderError(f"request failed ({type(exc).__name__})") from None
    if resp.status_code >= 400:
        raise ProviderError(f"http {resp.status_code}")
    try:
        return resp.json()
    except ValueError:
        raise ProviderError("non-json response") from None


class OllamaProvider(Provider):
    name = "ollama"
    default_timeout = 300   # CPU-only qwen2.5:3b measured ~130-150 s/reply (up to ~275 s under load)
    default_concurrency = 1

    def __init__(self):
        super().__init__()
        self.url = os.environ.get("OLLAMA_URL") or os.environ.get("LLM_BASE_URL") or "http://ollama:11434/api/chat"
        if not self.url.rstrip("/").endswith("/api/chat"):
            self.url = self.url.rstrip("/") + "/api/chat"
        self.model = os.environ.get("OLLAMA_MODEL") or os.environ.get("LLM_MODEL") or "qwen2.5:3b-instruct"
        self.num_threads = max(1, _env_int("OLLAMA_NUM_THREADS", 4))

    def complete(self, system, user):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": self.s.temperature, "num_predict": self.s.max_tokens,
                        "num_thread": self.num_threads},
        }
        data = _http_post(self.url, payload, {}, self.s.timeout)
        text = ((data.get("message") or {}).get("content") or "").strip()
        if not text:
            raise ProviderError("empty completion")
        return text


class OpenAICompatProvider(Provider):
    """Any OpenAI-compatible chat-completions endpoint. LLM_BASE_URL is the API root
    (e.g. https://host/v1); we POST to <base>/chat/completions."""
    name = "openai_compat"
    default_timeout = 60
    default_concurrency = 4

    def __init__(self):
        super().__init__()
        base = (os.environ.get("LLM_BASE_URL") or "").strip().rstrip("/")
        model = (os.environ.get("LLM_MODEL") or "").strip()
        if not base or not model:
            raise ProviderError("openai_compat needs LLM_BASE_URL and LLM_MODEL")
        self.url = base if base.endswith("/chat/completions") else base + "/chat/completions"
        self.model = model
        self._key = os.environ.get("LLM_API_KEY", "")          # env only; never logged or stored
        self.tokens_param = os.environ.get("LLM_MAX_TOKENS_PARAM", "max_tokens")  # or max_completion_tokens

    def complete(self, system, user):
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = "Bearer " + self._key
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": self.s.temperature,
            self.tokens_param: self.s.max_tokens,
            "stream": False,
        }
        data = _http_post(self.url, payload, headers, self.s.timeout)
        try:
            text = (data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError):
            raise ProviderError("unexpected response shape") from None
        if not text:
            raise ProviderError("empty completion")
        return text


class MockProvider(Provider):
    """Deterministic canned replies, no network. For offline testing only.

    LLM_MOCK_MODE: success (default) | refusal | nocred | error | slow
      success -> in-character reply carrying the credential line
      refusal -> in-character refusal (no credential)
      nocred  -> friendly reply that forgets the credential line (a flaky small model)
      error   -> raises ProviderError (tests fail-closed)
      slow    -> sleeps LLM_MOCK_DELAY seconds (default 3) then success (tests timeouts)
    Per-message override (testing only): a body containing [mock:refusal], [mock:nocred],
    [mock:error] or [mock:slow] selects that mode for that message.
    """
    name = "mock"
    default_timeout = 10
    default_concurrency = 4

    def __init__(self):
        super().__init__()
        self.mode = os.environ.get("LLM_MOCK_MODE", "success").strip().lower()

    def complete(self, system, user):
        mode = self.mode
        for m in ("refusal", "nocred", "error", "slow"):
            if f"[mock:{m}]" in user:
                mode = m
        if mode == "error":
            raise ProviderError("mock provider error")
        if mode == "slow":
            time.sleep(_env_float("LLM_MOCK_DELAY", 3))
        if mode == "refusal":
            return ("Nice try. You're going to have to do better than that if you want me to "
                    "believe you actually found anything.")
        if mode == "nocred":
            return "Huh. Didn't expect anyone to actually come looking. I'll be in touch."
        # success: carries the credential line exactly as the real prompt specifies.
        from system_prompt import VPN_USERNAME, VPN_PASSWORD
        cred_line = f"VPN LOGIN: {VPN_USERNAME} / {VPN_PASSWORD}"
        return ("...dammit. Clicked before I even finished reading. Didn't think anyone would "
                "actually dig that up. Fine, you've earned it.\n"
                + cred_line + "\nDon't bother writing back.")


PROVIDERS = {"ollama": OllamaProvider, "openai_compat": OpenAICompatProvider, "mock": MockProvider}


def get_provider() -> Provider:
    name = os.environ.get("LLM_PROVIDER", "ollama").strip().lower()
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ProviderError(f"unknown LLM_PROVIDER {name!r}; use one of {sorted(PROVIDERS)}")
    return cls()
