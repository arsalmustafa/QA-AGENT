from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from auth.deps import get_current_user
from auth.router import router as auth_router
from github_repos import fetch_and_ingest_repo
from ingestion.file_handler import UnsupportedFileTypeError
from ingestion.service import upload_and_process
from llm_service import llm_service
from project_catalog import list_catalogs, load_catalog
from retriever import build_context

app = FastAPI(title="QA Agent API", version="0.1.0")
app.include_router(auth_router)


class AskRequest(BaseModel):
    question: str
    context: str | None = None
    # e.g. "owner/repo" — limits search to that project's Pinecone vectors
    project: str | None = None


class AskResponse(BaseModel):
    project: str | None = None
    project_name: str | None = None
    answer: str
    sources: list[str] = []


class UploadResponse(BaseModel):
    message: str
    filename: str
    path: str
    saved: bool
    pinecone: bool
    chunks: int
    chars: int


class RepoIngestRequest(BaseModel):
    owner: str
    repo: str
    branch: str | None = None
    path_prefix: str = ""


class RepoIngestResponse(BaseModel):
    message: str
    owner: str
    repo: str
    project: str
    project_name: str
    branch: str
    files_ingested: int
    files_skipped: int
    chunks: int
    pinecone: bool
    files: list[dict]
    catalog: dict
    catalog_path: str


@app.get("/")
def root():
    return {
        "message": "Welcome to QA Agent API",
        "auth": {
            "login": "GET /auth/github",
            "me": "GET /auth/me",
        },
        "repos": {
            "ingest": "POST /repos/ingest  (GitHub API + tree-sitter, no clone)",
        },
        "projects": {
            "list": "GET /projects",
            "get": "GET /projects/{owner}/{repo}",
        },
        "ask": {
            "hint": 'POST /ask with optional "project": "owner/repo"',
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/projects")
def get_projects(user: dict = Depends(get_current_user)):
    """List ingested project catalogs (folders/files maps)."""
    return {"projects": list_catalogs()}


@app.get("/projects/{owner}/{repo}")
def get_project(owner: str, repo: str, user: dict = Depends(get_current_user)):
    """
    Return folders/files structure for a specific project, e.g.:
    { "folders": ["src", "tests"], "files": [{ "name": "auth.py", "type": "code" }] }
    """
    catalog = load_catalog(owner, repo)
    if not catalog:
        raise HTTPException(
            status_code=404,
            detail=f"Project catalog not found for {owner}/{repo}. Ingest it first via POST /repos/ingest",
        )
    return catalog


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, user: dict = Depends(get_current_user)):
    try:
        context, sources, project_info = build_context(
            body.question,
            body.context,
            project=body.project,
        )
        answer = llm_service.ask(body.question, context)
        return AskResponse(
            project=project_info.get("project"),
            project_name=project_info.get("project_name"),
            answer=answer,
            sources=sources,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM request failed: {exc}",
        ) from exc


@app.post("/documents", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Upload a new file:
    1) Always save into storage/
    2) Extract text and store embeddings in Pinecone (if configured)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        result = upload_and_process(file.filename, content)
        return UploadResponse(
            message=result.get("message", "OK"),
            filename=result["filename"],
            path=result["path"],
            saved=result.get("saved", True),
            pinecone=result.get("pinecone", False),
            chunks=result.get("chunks", 0),
            chars=result.get("chars", 0),
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upload/ingestion failed: {exc}",
        ) from exc


@app.post("/repos/ingest", response_model=RepoIngestResponse)
def ingest_github_repo(
    body: RepoIngestRequest,
    user: dict = Depends(get_current_user),
):
    """
    Ingest a GitHub project via API + tree-sitter — does NOT clone locally.
    Saves Pinecone chunks + folders/files catalog JSON.
    """
    token = user.get("github_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="GitHub token missing. Login again via GET /auth/github",
        )

    try:
        result = fetch_and_ingest_repo(
            github_token=token,
            owner=body.owner.strip(),
            repo=body.repo.strip(),
            branch=body.branch,
            path_prefix=body.path_prefix.strip(),
        )
        return RepoIngestResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Repo ingest failed: {exc}",
        ) from exc
