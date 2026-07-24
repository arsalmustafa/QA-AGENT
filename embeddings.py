import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

OLLAMA_EMBED_URL = os.getenv(
    "OLLAMA_EMBED_URL",
    "http://localhost:11434/api/embeddings",
)
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
# nomic-embed-text outputs 768-dimensional vectors
EMBED_DIMENSION = int(os.getenv("EMBED_DIMENSION", "768"))


def embed_text(text: str) -> list[float]:
    """Create an embedding vector using Ollama."""
    payload = {
        "model": OLLAMA_EMBED_MODEL,
        "prompt": text,
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(OLLAMA_EMBED_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    embedding = data.get("embedding")
    if not embedding:
        raise RuntimeError("Ollama returned no embedding. Is the embed model pulled?")

    return embedding
