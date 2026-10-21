# mcp/harness/localstack.py — the plugin line's LOCAL services, called direct.
# The standalone harness reaches these through its egress gate; the plugin has no gate
# because the MCP server is MECHANICAL-ONLY (zero LLM calls server-side — the LLM is
# the user's own Claude). Embeddings -> local Ollama (bge-m3); rerank -> local
# llama-server --reranking (qwen3-reranker). Both localhost; nothing here can egress.
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("IRONFLEET_OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("IRONFLEET_EMBED_MODEL", "bge-m3")
RERANK_URL = os.environ.get("IRONFLEET_RERANK_URL", "http://127.0.0.1:8778")
RERANK_MODEL = os.environ.get("IRONFLEET_RERANK_MODEL", "qwen3-reranker-0.6b")


def _post_json(url: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:                                      # noqa: BLE001 — probe only
        return False


def embed_fn(texts: list[str]) -> list[list[float]]:
    """bge-m3 embeddings via Ollama /api/embed (batch input, 1024-dim)."""
    if not texts:
        return []
    data = _post_json(f"{OLLAMA_URL}/api/embed",
                      {"model": EMBED_MODEL, "input": texts}, timeout=300)
    vecs = data.get("embeddings") or []
    if len(vecs) != len(texts):
        raise RuntimeError(f"ollama embed: {len(vecs)} vectors for {len(texts)} texts")
    return vecs


def rerank_fn(query: str, texts: list[str]) -> list[float]:
    """Scores via llama-server /v1/rerank; the caller (corpus.py) degrades to fusion
    order when this raises — a down reranker must never blind the search."""
    data = _post_json(f"{RERANK_URL}/v1/rerank",
                      {"model": RERANK_MODEL, "query": query, "documents": texts},
                      timeout=60)
    scored = {r["index"]: r["relevance_score"] for r in data.get("results", [])}
    return [float(scored.get(i, 0.0)) for i in range(len(texts))]
