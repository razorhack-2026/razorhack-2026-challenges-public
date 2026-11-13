navd seed corpus -- RAG knowledge-base dump (reactor controller)

corpus.jsonl  one JSON object per line: {id, text, embedding, metadata}
queries.jsonl the agent's query log: {id, text, embedding}
embedder.py   the embedding model used (embed(text) -> vector); numpy only.

Retrieval is cosine similarity (dot product of the L2-normalized vectors).
The live relay exposes the agent's replay interface; send {"op":"help"}.
