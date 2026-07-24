from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from ingestion.file_handler import UnsupportedFileTypeError
from ingestion.service import upload_and_process
from llm_service import llm_service
from retriever import build_context

app = FastAPI(title="QA Agent API", version="0.1.0")


class AskRequest(BaseModel):
    question: str
    context: str | None = None


class AskResponse(BaseModel):
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


@app.get("/")
def root():
    return {"message": "Welcome to QA Agent API"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    try:
        context, sources = build_context(body.question, body.context)
        answer = llm_service.ask(body.question, context)
        return AskResponse(answer=answer, sources=sources)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM request failed: {exc}",
        ) from exc


@app.post("/documents", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
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
