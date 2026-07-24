"""
Local hybrid reranker (no torch / no cloud API).

Takes Pinecone candidates (e.g. top 10) and re-scores them using:
  final = 0.6 * vector_score + 0.4 * bm25_score
then keeps the best N chunks for the LLM.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

load_dotenv(Path(__file__).resolve().parent / ".env")

RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "3"))
VECTOR_WEIGHT = float(os.getenv("RERANK_VECTOR_WEIGHT", "0.6"))
BM25_WEIGHT = float(os.getenv("RERANK_BM25_WEIGHT", "0.4"))


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def _normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return [1.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def rerank(question: str, hits: list[dict], top_n: int | None = None) -> list[dict]:
    """
    Re-score retrieved chunks and keep the best ones.
    """
    if not hits:
        return []

    keep = top_n if top_n is not None else RERANK_TOP_N
    keep = max(1, min(keep, len(hits)))

    if len(hits) == 1:
        item = dict(hits[0])
        item["rerank_score"] = float(hits[0].get("score") or 0.0)
        return [item]

    corpus = [_tokenize(hit["text"]) for hit in hits]
    bm25 = BM25Okapi(corpus)
    bm25_raw = list(bm25.get_scores(_tokenize(question)))
    bm25_norm = _normalize(bm25_raw)

    vector_raw = [float(hit.get("score") or 0.0) for hit in hits]
    vector_norm = _normalize(vector_raw)

    ranked: list[tuple[dict, float]] = []
    for hit, v_score, b_score in zip(hits, vector_norm, bm25_norm):
        final = VECTOR_WEIGHT * v_score + BM25_WEIGHT * b_score
        ranked.append((hit, final))

    ranked.sort(key=lambda item: item[1], reverse=True)

    results: list[dict] = []
    for hit, score in ranked[:keep]:
        item = dict(hit)
        item["rerank_score"] = float(score)
        results.append(item)
    return results
