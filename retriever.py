import os
from pathlib import Path
import re

from dotenv import load_dotenv

from pinecone_client import get_index, is_pinecone_configured
from embeddings import embed_text
from ingestion.file_handler import SUPPORTED_EXTENSIONS, extract_text
from reranker import rerank

load_dotenv(Path(__file__).resolve().parent / ".env")

ROOT_DIR = Path(__file__).resolve().parent
STORAGE_DIR = ROOT_DIR / "storage"

# Fetch more candidates from Pinecone, then rerank down
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "10"))
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "3"))


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) > 2}


def _iter_local_files():
    if not STORAGE_DIR.exists():
        return
    for path in sorted(STORAGE_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def _load_chunks() -> list[dict]:
    chunks: list[dict] = []

    for path in _iter_local_files():
        try:
            text = extract_text(path)
        except Exception:
            continue
        if not text:
            continue

        parts = re.split(r"(?=^##\s)", text, flags=re.MULTILINE)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            chunks.append(
                {
                    "source": path.name,
                    "text": part,
                    "tokens": _tokenize(part),
                }
            )

    return chunks


def retrieve_keyword(question: str, top_k: int = RETRIEVE_TOP_K, min_score: int = 1) -> list[dict]:
    """Fallback: simple keyword retrieval over storage/."""
    question_tokens = _tokenize(question)
    if not question_tokens:
        return []

    scored: list[dict] = []
    for chunk in _load_chunks():
        overlap = question_tokens & chunk["tokens"]
        score = len(overlap)
        if score >= min_score:
            scored.append(
                {
                    "source": chunk["source"],
                    "text": chunk["text"],
                    "score": float(score),
                }
            )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def retrieve_pinecone(question: str, top_k: int = RETRIEVE_TOP_K) -> list[dict]:
    """Semantic retrieval using embeddings + Pinecone."""
    vector = embed_text(question)
    index = get_index()
    result = index.query(vector=vector, top_k=top_k, include_metadata=True)

    matches = getattr(result, "matches", None)
    if matches is None and isinstance(result, dict):
        matches = result.get("matches", [])

    hits: list[dict] = []
    for match in matches or []:
        metadata = getattr(match, "metadata", None)
        if metadata is None and isinstance(match, dict):
            metadata = match.get("metadata")
        metadata = metadata or {}

        text = metadata.get("text", "")
        source = metadata.get("source", "unknown")
        if not text:
            continue

        score = getattr(match, "score", None)
        if score is None and isinstance(match, dict):
            score = match.get("score")

        hits.append(
            {
                "source": source,
                "text": text,
                "score": float(score or 0.0),
            }
        )
    return hits


def retrieve(question: str, top_k: int = RETRIEVE_TOP_K) -> list[dict]:
    """
    Retrieve candidates (default top 10), then rerank to best N.
    """
    if is_pinecone_configured():
        hits = retrieve_pinecone(question, top_k=top_k)
    else:
        print(
            "PINECONE_API_KEY not set — using keyword fallback on storage/. "
            "Add your key to .env, then upload files via POST /documents"
        )
        hits = retrieve_keyword(question, top_k=top_k)

    return rerank(question, hits, top_n=RERANK_TOP_N)


def build_context(question: str, extra_context: str | None = None) -> tuple[str | None, list[str]]:
    """
    Build final context from retrieved + reranked docs + optional user context.
    Returns (context_text, source_names).
    """
    hits = retrieve(question)
    parts: list[str] = []
    sources: list[str] = []

    if hits:
        retrieved = "\n\n---\n\n".join(
            f"Source: {hit['source']}\n{hit['text']}" for hit in hits
        )
        parts.append(retrieved)
        for hit in hits:
            if hit["source"] not in sources:
                sources.append(hit["source"])

    if extra_context and extra_context.strip():
        parts.append(f"Source: user\n{extra_context.strip()}")
        if "user" not in sources:
            sources.append("user")

    if not parts:
        return None, []

    return "\n\n====\n\n".join(parts), sources
