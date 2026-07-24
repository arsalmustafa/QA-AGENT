"""Embed chunks and upsert into Pinecone."""

from embeddings import embed_text
from pinecone_client import get_index, is_pinecone_configured


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
        values = embed_text(chunk["text"])
        vectors.append(
            {
                "id": chunk["id"],
                "values": values,
                "metadata": {
                    "source": chunk["source"],
                    "text": chunk["text"],
                },
            }
        )

    # Upsert in batches of 50
    batch_size = 50
    for start in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[start : start + batch_size])

    return len(vectors)
