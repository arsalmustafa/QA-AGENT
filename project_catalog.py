"""Project catalog: folders/files map saved per ingested repo."""

from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = ROOT_DIR / "storage" / "projects"


def ensure_projects_dir() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def project_id(owner: str, repo: str) -> str:
    return f"{owner}/{repo}"


def catalog_path(owner: str, repo: str) -> Path:
    ensure_projects_dir()
    safe = f"{owner}__{repo}.json".replace(" ", "_")
    return PROJECTS_DIR / safe


def build_catalog(
    *,
    owner: str,
    repo: str,
    branch: str,
    file_entries: list[dict],
) -> dict:
    """
    Build a folders/files project map.

    file_entries items:
      { path, type: "code"|"documentation", language?, symbols?: [...] }
    """
    folders: set[str] = set()
    files: list[dict] = []

    for entry in file_entries:
        path = entry["path"].replace("\\", "/")
        parent = str(Path(path).parent).replace("\\", "/")
        if parent and parent != ".":
            # add each folder level: src, src/auth
            parts = parent.split("/")
            for i in range(len(parts)):
                folders.add("/".join(parts[: i + 1]))

        item = {
            "name": Path(path).name,
            "path": path,
            "type": entry.get("type") or "documentation",
        }
        if entry.get("language"):
            item["language"] = entry["language"]
        if entry.get("symbols"):
            item["symbols"] = entry["symbols"]
        files.append(item)

    return {
        "project": project_id(owner, repo),
        "project_name": repo,
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "folders": sorted(folders),
        "files": files,
    }


def save_catalog(catalog: dict) -> Path:
    owner = catalog["owner"]
    repo = catalog["repo"]
    path = catalog_path(owner, repo)
    path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return path


def load_catalog(owner: str, repo: str) -> dict | None:
    path = catalog_path(owner, repo)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_catalogs() -> list[dict]:
    ensure_projects_dir()
    items: list[dict] = []
    for path in sorted(PROJECTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "project": data.get("project"),
                    "project_name": data.get("project_name"),
                    "owner": data.get("owner"),
                    "repo": data.get("repo"),
                    "branch": data.get("branch"),
                    "folders_count": len(data.get("folders") or []),
                    "files_count": len(data.get("files") or []),
                    "catalog_path": str(path),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return items
