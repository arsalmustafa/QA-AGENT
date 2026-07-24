import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

from embeddings import EMBED_DIMENSION

load_dotenv(Path(__file__).resolve().parent / ".env")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "").strip()
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "qa-agent")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")


def is_pinecone_configured() -> bool:
    return bool(PINECONE_API_KEY) and PINECONE_API_KEY != "your_pinecone_api_key_here"


@lru_cache(maxsize=1)
def get_pinecone_client() -> Pinecone:
    if not is_pinecone_configured():
        raise RuntimeError(
            "PINECONE_API_KEY is missing. Add it to your .env file."
        )
    return Pinecone(api_key=PINECONE_API_KEY)


def ensure_index() -> None:
    """Create the Pinecone index if it does not already exist."""
    pc = get_pinecone_client()
    existing = {idx.name for idx in pc.list_indexes()}

    if PINECONE_INDEX in existing:
        return

    pc.create_index(
        name=PINECONE_INDEX,
        dimension=EMBED_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
    )


def get_index():
    ensure_index()
    return get_pinecone_client().Index(PINECONE_INDEX)
