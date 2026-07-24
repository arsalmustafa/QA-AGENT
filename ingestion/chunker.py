"""Split extracted text into chunks for embedding."""

from pathlib import Path
import re


def chunk_text(text: str, source: str, max_chars: int = 1200) -> list[dict]:
    """
    Split text into chunks.
    Prefers markdown ## sections when present; otherwise packs by size.
    """
    text = text.strip()
    if not text:
        return []

    if re.search(r"^##\s", text, flags=re.MULTILINE):
        parts = re.split(r"(?=^##\s)", text, flags=re.MULTILINE)
    else:
        parts = _split_by_size(text, max_chars)

    stem = Path(source).stem
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-").lower() or "doc"

    chunks: list[dict] = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        for j, piece in enumerate(_split_by_size(part, max_chars)):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                {
                    "id": f"{safe}-{i}-{j}",
                    "source": source,
                    "text": piece,
                }
            )
    return chunks


def _split_by_size(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    paragraphs = re.split(r"\n\s*\n", text)
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if not current:
            current = para
        elif len(current) + 2 + len(para) <= max_chars:
            current = f"{current}\n\n{para}"
        else:
            parts.append(current)
            current = para

    if current:
        parts.append(current)

    final: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            final.append(part)
        else:
            for start in range(0, len(part), max_chars):
                final.append(part[start : start + max_chars])
    return final
