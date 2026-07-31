"""Orchestrate: save to storage → extract text → chunk → Pinecone."""

from pathlib import Path
import uuid

from ingestion.chunker import chunk_text
from ingestion.file_handler import SUPPORTED_EXTENSIONS, extract_text
from ingestion.store import upsert_chunks
from pinecone_client import is_pinecone_configured

ROOT_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = ROOT_DIR / "storage"


def ensure_storage() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_to_storage(filename: str, content: bytes) -> Path:
    """Save uploaded bytes into storage/ (independent of Pinecone)."""
    ensure_storage()
    safe_name = Path(filename).name
    unique = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    path = STORAGE_DIR / unique
    path.write_bytes(content)
    return path


def process_stored_file(path: Path) -> dict:
    """
    Extract text from a stored file, chunk, embed, upsert to Pinecone.
    """
    text = extract_text(path)
    if not text:
        raise ValueError(f"No text could be extracted from {path.name}")

    chunks = chunk_text(text, source=path.name)
    enriched = [
        {
            **c,
            "project": "",
            "project_name": "",
            "owner": "",
            "repo": "",
            "path": path.name,
            "type": "doc",
            "language": "text",
            "symbol": "",
            "kind": "file",
        }
        for c in chunks
    ]
    count = upsert_chunks(enriched)

    return {
        "filename": path.name,
        "path": str(path),
        "chunks": count,
        "chars": len(text),
        "pinecone": True,
    }


def upload_and_process(filename: str, content: bytes) -> dict:
    """
    1) Always save file to storage/
    2) Then extract text and push embeddings to Pinecone (if configured)
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Step 1: save first — never depends on Pinecone / docs
    path = save_to_storage(filename, content)
    result = {
        "filename": path.name,
        "path": str(path),
        "chunks": 0,
        "chars": 0,
        "pinecone": False,
        "saved": True,
    }

    # Step 2: extract + store vectors (optional if key missing)
    if not is_pinecone_configured():
        text = extract_text(path)
        result["chars"] = len(text)
        result["message"] = (
            "File saved to storage. "
            "Add PINECONE_API_KEY to embed it into Pinecone."
        )
        return result

    processed = process_stored_file(path)
    result.update(processed)
    result["saved"] = True
    result["message"] = "File saved to storage and ingested into Pinecone."
    return result


def ingest_all_storage_files() -> list[dict]:
    """Re-process every file currently in storage/."""
    ensure_storage()
    results: list[dict] = []

    for path in sorted(STORAGE_DIR.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        results.append(process_stored_file(path))

    return results
