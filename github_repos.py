"""Fetch GitHub repo files via API (PyGithub) — no local git clone."""

from __future__ import annotations

from pathlib import Path

from github import Auth, Github, GithubException

from ingestion.chunker import chunk_text
from ingestion.service import ensure_storage, save_to_storage
from ingestion.store import upsert_chunks
from pinecone_client import is_pinecone_configured

# Text / code files we ingest from repos
REPO_TEXT_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".env.example",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".html",
    ".css",
    ".scss",
    ".xml",
    ".dockerfile",
}

SKIP_DIR_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "target",
    "vendor",
    ".idea",
    ".vscode",
}

MAX_FILE_BYTES = 500_000  # skip huge files
MAX_FILES = 200  # safety limit per ingest


def _should_skip_path(path: str) -> bool:
    parts = Path(path).parts
    if any(part in SKIP_DIR_PARTS for part in parts):
        return True
    return not _is_supported_repo_file(path)


def _is_supported_repo_file(path: str) -> bool:
    name = Path(path).name.lower()
    suffix = Path(path).suffix.lower()
    if name in {"dockerfile", "makefile", "readme", "license", "licence"}:
        return True
    if name.startswith("readme."):
        return True
    return suffix in REPO_TEXT_EXTENSIONS


def fetch_and_ingest_repo(
    github_token: str,
    owner: str,
    repo: str,
    branch: str | None = None,
    path_prefix: str = "",
) -> dict:
    """
    Read repo content through GitHub API (no clone) and ingest into Pinecone.
    """
    if not github_token:
        raise ValueError("GitHub access token is missing. Login again via /auth/github")

    gh = Github(auth=Auth.Token(github_token))
    try:
        repository = gh.get_repo(f"{owner}/{repo}")
    except GithubException as exc:
        raise ValueError(f"Could not open repo {owner}/{repo}: {exc.data}") from exc

    ref = branch or repository.default_branch

    try:
        tree = repository.get_git_tree(ref, recursive=True)
    except GithubException as exc:
        raise ValueError(f"Could not read tree for branch '{ref}': {exc.data}") from exc

    ensure_storage()
    ingested: list[dict] = []
    skipped = 0
    total_chunks = 0

    for element in tree.tree:
        if element.type != "blob":
            continue
        file_path = element.path
        if path_prefix and not file_path.startswith(path_prefix):
            continue
        if _should_skip_path(file_path) or not _is_supported_repo_file(file_path):
            skipped += 1
            continue
        if element.size is not None and element.size > MAX_FILE_BYTES:
            skipped += 1
            continue
        if len(ingested) >= MAX_FILES:
            break

        try:
            content_file = repository.get_contents(file_path, ref=ref)
            # get_contents can return a list for directories; we only want files
            if isinstance(content_file, list):
                skipped += 1
                continue
            raw = content_file.decoded_content
            if raw is None:
                skipped += 1
                continue
            text = raw.decode("utf-8", errors="ignore").strip()
            if not text:
                skipped += 1
                continue
        except (GithubException, UnicodeError, AttributeError):
            skipped += 1
            continue

        source_name = f"{owner}__{repo}__{file_path.replace('/', '__')}"
        # Save a local text copy under storage/ for traceability
        safe_name = source_name.replace(" ", "_")
        if not Path(safe_name).suffix:
            safe_name = f"{safe_name}.txt"
        path = save_to_storage(safe_name, text.encode("utf-8"))

        chunks = chunk_text(text, source=f"{owner}/{repo}:{file_path}")
        chunk_count = 0
        if is_pinecone_configured() and chunks:
            chunk_count = upsert_chunks(chunks)
            total_chunks += chunk_count

        ingested.append(
            {
                "path": file_path,
                "saved_as": path.name,
                "chars": len(text),
                "chunks": chunk_count,
            }
        )

    return {
        "owner": owner,
        "repo": repo,
        "branch": ref,
        "files_ingested": len(ingested),
        "files_skipped": skipped,
        "chunks": total_chunks,
        "pinecone": is_pinecone_configured(),
        "files": ingested,
        "message": (
            f"Ingested {len(ingested)} files from {owner}/{repo}@{ref} via GitHub API (no clone)."
        ),
    }
