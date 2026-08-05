"""Embed chunks and upsert into Pinecone (with project metadata)."""

from embeddings import embed_text
from pinecone_client import get_index, is_pinecone_configured

# Pinecone metadata string fields — keep values bounded
_META_TEXT_MAX = 35000


def upsert_chunks(chunks: list[dict]) -> int:
    """Embed and store chunks in Pinecone. Returns number upserted."""
    if not is_pinecone_configured():
        raise RuntimeError(
            "PINECONE_API_KEY is missing. Add it to your .env file."
        )

    if not chunks:
        return 0

    index = get_index()
    vectors = []

    for chunk in chunks:
        text = chunk.get("text") or ""
        values = embed_text(text)
        metadata = {
            "source": str(chunk.get("source") or ""),
            "text": text[:_META_TEXT_MAX],
            "project": str(chunk.get("project") or ""),
            "project_name": str(chunk.get("project_name") or ""),
            "owner": str(chunk.get("owner") or ""),
            "repo": str(chunk.get("repo") or ""),
            "path": str(chunk.get("path") or ""),
            "type": str(chunk.get("type") or "doc"),
            "language": str(chunk.get("language") or ""),
            "symbol": str(chunk.get("symbol") or ""),
            "kind": str(chunk.get("kind") or ""),
        }
        # Drop empty optional fields? Keep them for consistent filtering.
        vectors.append(
            {
                "id": str(chunk["id"])[:512],
                "values": values,
                "metadata": metadata,
            }
        )

    batch_size = 50
    for start in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[start : start + batch_size])

    return len(vectors)
