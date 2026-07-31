"""Fetch GitHub repo files via API (PyGithub) — no local git clone."""

from __future__ import annotations

from pathlib import Path

from github import Auth, Github, GithubException

from ingestion.chunker import chunk_text
from ingestion.code_chunker import EXT_TO_LANG, chunk_code
from ingestion.service import ensure_storage, save_to_storage
from ingestion.store import upsert_chunks
from pinecone_client import is_pinecone_configured

# Text / code files we ingest from repos
REPO_TEXT_EXTENSIONS = set(EXT_TO_LANG.keys()) | {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".csv",
    ".ini",
    ".cfg",
    ".env.example",
    ".xml",
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

MAX_FILE_BYTES = 500_000
MAX_FILES = 200


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


def _is_code_file(path: str) -> bool:
    return Path(path).suffix.lower() in EXT_TO_LANG


def fetch_and_ingest_repo(
    github_token: str,
    owner: str,
    repo: str,
    branch: str | None = None,
    path_prefix: str = "",
) -> dict:
    """
    Read ALL supported files for a project via GitHub API (no clone),
    chunk code with tree-sitter, and store in Pinecone tagged by project.
    """
    if not github_token:
        raise ValueError("GitHub access token is missing. Login again via /auth/github")

    gh = Github(auth=Auth.Token(github_token))
    try:
        repository = gh.get_repo(f"{owner}/{repo}")
    except GithubException as exc:
        raise ValueError(f"Could not open repo {owner}/{repo}: {exc.data}") from exc

    ref = branch or repository.default_branch
    project = f"{owner}/{repo}"
    project_name = repo

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
        safe_name = source_name.replace(" ", "_")
        if not Path(safe_name).suffix:
            safe_name = f"{safe_name}.txt"
        path = save_to_storage(safe_name, text.encode("utf-8"))

        source = f"{project}:{file_path}"
        if _is_code_file(file_path):
            chunks = chunk_code(
                text,
                source=source,
                path=file_path,
                project=project,
                project_name=project_name,
                owner=owner,
                repo=repo,
            )
        else:
            # Docs / config in the repo — still tagged with project
            plain = chunk_text(text, source=source)
            chunks = [
                {
                    **c,
                    "id": f"{owner}-{repo}-{c['id']}"[:200],
                    "project": project,
                    "project_name": project_name,
                    "owner": owner,
                    "repo": repo,
                    "path": file_path,
                    "type": "doc",
                    "language": "markdown" if file_path.endswith((".md", ".markdown")) else "text",
                    "symbol": "",
                    "kind": "file",
                }
                for c in plain
            ]

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
                "code": _is_code_file(file_path),
            }
        )

    return {
        "owner": owner,
        "repo": repo,
        "project": project,
        "project_name": project_name,
        "branch": ref,
        "files_ingested": len(ingested),
        "files_skipped": skipped,
        "chunks": total_chunks,
        "pinecone": is_pinecone_configured(),
        "files": ingested,
        "message": (
            f"Ingested {len(ingested)} files from project {project}@{ref} "
            f"via GitHub API + tree-sitter (no clone)."
        ),
    }
