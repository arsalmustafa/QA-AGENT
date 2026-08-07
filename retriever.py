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
                    "project": "",
                    "project_name": "",
                }
            )

    return chunks


CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".swift",
    ".kt",
    ".scala",
}

DOC_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".pdf", ".csv"}

# Path substrings used to prefer security-relevant hits locally
SECURITY_PATH_HINTS = (
    "auth",
    "security",
    "jwt",
    "oauth",
    "token",
    "secret",
    "password",
    "permission",
    "rbac",
    "crypto",
    "session",
    "credential",
    "login",
    "middleware",
)


def _pinecone_filter(
    project: str | None = None,
    chunk_type: str | None = None,
) -> dict | None:
    """Build Pinecone metadata filter from optional project + chunk type."""
    clauses: list[dict] = []
    if project and project.strip():
        clauses.append({"project": {"$eq": project.strip()}})
    if chunk_type and chunk_type.strip():
        clauses.append({"type": {"$eq": chunk_type.strip()}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _source_looks_like_code(source: str) -> bool:
    return Path(source).suffix.lower() in CODE_EXTENSIONS


def _source_looks_like_doc(source: str) -> bool:
    suffix = Path(source).suffix.lower()
    if suffix in DOC_EXTENSIONS:
        return True
    name = Path(source).name.lower()
    return name.startswith("readme") or name in {"license", "licence"}


def _path_matches_security(path: str, source: str) -> bool:
    hay = f"{path} {source}".lower()
    return any(hint in hay for hint in SECURITY_PATH_HINTS)


def _prefer_security_hits(hits: list[dict]) -> list[dict]:
    """If any security-ish paths exist, keep those; otherwise keep all."""
    preferred = [
        h
        for h in hits
        if _path_matches_security(h.get("path") or "", h.get("source") or "")
    ]
    return preferred or hits


def retrieve_keyword(
    question: str,
    top_k: int = RETRIEVE_TOP_K,
    min_score: int = 1,
    project: str | None = None,
    chunk_type: str | None = None,
) -> list[dict]:
    """Fallback: simple keyword retrieval over storage/."""
    question_tokens = _tokenize(question)
    if not question_tokens:
        return []

    project_key = (project or "").strip().lower()
    type_key = (chunk_type or "").strip().lower()
    scored: list[dict] = []
    for chunk in _load_chunks():
        if project_key and project_key not in chunk["source"].lower():
            continue
        if type_key == "code" and not _source_looks_like_code(chunk["source"]):
            continue
        if type_key == "doc" and not _source_looks_like_doc(chunk["source"]):
            continue
        overlap = question_tokens & chunk["tokens"]
        score = len(overlap)
        if score >= min_score:
            scored.append(
                {
                    "source": chunk["source"],
                    "text": chunk["text"],
                    "score": float(score),
                    "project": chunk.get("project") or "",
                    "project_name": chunk.get("project_name") or "",
                    "path": "",
                    "symbol": "",
                    "type": "code"
                    if _source_looks_like_code(chunk["source"])
                    else "doc",
                }
            )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def retrieve_pinecone(
    question: str,
    top_k: int = RETRIEVE_TOP_K,
    project: str | None = None,
    chunk_type: str | None = None,
) -> list[dict]:
    """Semantic retrieval using embeddings + Pinecone (optional filters)."""
    vector = embed_text(question)
    index = get_index()

    query_kwargs: dict = {
        "vector": vector,
        "top_k": top_k,
        "include_metadata": True,
    }
    meta_filter = _pinecone_filter(project=project, chunk_type=chunk_type)
    if meta_filter:
        query_kwargs["filter"] = meta_filter

    result = index.query(**query_kwargs)

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
                "project": metadata.get("project") or "",
                "project_name": metadata.get("project_name") or "",
                "path": metadata.get("path") or "",
                "symbol": metadata.get("symbol") or "",
                "type": metadata.get("type") or "",
            }
        )
    return hits


def retrieve(
    question: str,
    top_k: int = RETRIEVE_TOP_K,
    project: str | None = None,
    chunk_type: str | None = None,
    prefer_security_paths: bool = False,
) -> list[dict]:
    """Retrieve candidates (default top 10), then rerank to best N."""
    # Fetch a bit more when we will narrow to security paths
    fetch_k = top_k * 2 if prefer_security_paths else top_k

    if is_pinecone_configured():
        hits = retrieve_pinecone(
            question,
            top_k=fetch_k,
            project=project,
            chunk_type=chunk_type,
        )
    else:
        print(
            "PINECONE_API_KEY not set — using keyword fallback on storage/. "
            "Add your key to .env, then upload files via POST /documents"
        )
        hits = retrieve_keyword(
            question,
            top_k=fetch_k,
            project=project,
            chunk_type=chunk_type,
        )

    if prefer_security_paths:
        hits = _prefer_security_hits(hits)

    return rerank(question, hits, top_n=RERANK_TOP_N)


def build_context(
    question: str,
    extra_context: str | None = None,
    project: str | None = None,
    chunk_type: str | None = None,
    prefer_security_paths: bool = False,
) -> tuple[str | None, list[str], dict]:
    """
    Build final context from retrieved + reranked docs.
    Returns (context_text, source_names, project_info).
    """
    hits = retrieve(
        question,
        project=project,
        chunk_type=chunk_type,
        prefer_security_paths=prefer_security_paths,
    )
    parts: list[str] = []
    sources: list[str] = []

    project_info = {
        "project": (project or "").strip() or None,
        "project_name": None,
    }
    if hits:
        # Prefer metadata from hits
        for hit in hits:
            if hit.get("project_name"):
                project_info["project_name"] = hit["project_name"]
                project_info["project"] = hit.get("project") or project_info["project"]
                break
        if project_info["project"] and not project_info["project_name"]:
            project_info["project_name"] = project_info["project"].split("/")[-1]

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
        return None, [], project_info

    return "\n\n====\n\n".join(parts), sources, project_info
