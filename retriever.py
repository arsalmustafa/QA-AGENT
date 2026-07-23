from pathlib import Path
import re

DOCS_DIR = Path(__file__).resolve().parent / "docs"


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) > 2}


def _load_chunks() -> list[dict]:
    """Load markdown docs and split into chunks by headings/paragraphs."""
    chunks: list[dict] = []

    if not DOCS_DIR.exists():
        return chunks

    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        # Split on markdown headings; fall back to whole file
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


def retrieve(question: str, top_k: int = 3, min_score: int = 1) -> list[dict]:
    """
    Simple keyword retrieval over docs/.
    Returns top matching chunks: [{source, text, score}, ...]
    """
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
                    "score": score,
                }
            )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def build_context(question: str, extra_context: str | None = None) -> tuple[str | None, list[str]]:
    """
    Build final context from retrieved docs + optional user context.
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
