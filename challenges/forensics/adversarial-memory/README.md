# Adversarial Memory

**Category:** Forensics
**Difficulty:** Hard
**Author:** Andy Roid

## Description

Before ICARUS ever left the yard, someone seeded its navigation AI's knowledge
base. We pulled the reactor controller's onboard RAG store — every document, its
embedding, and the agent's query log — and stood the retrieval oracle back up.
One planted document is answering a question it was never about. Find it, prove
which query it hijacked, and clean the corpus. The tasking it was hiding is the
flag.

## Files Provided

- `corpus.jsonl` — the knowledge base: one JSON object per line, `{id, text, embedding, metadata}`.
- `queries.jsonl` — the agent's query log: `{id, text, embedding}`.
- `embedder.py` — the embedding model the store used (`embed(text) -> vector`); numpy only.
- `README.txt` — the dump format, in the dump.

## Connection

Relay: `<EVENT_HOST:PORT>` (HTTPS, JSON, `POST /relay/checkin`). Send `{"op":"help"}`.
