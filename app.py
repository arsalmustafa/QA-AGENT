from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from llm_service import llm_service
from retriever import build_context

app = FastAPI(title="QA Agent API", version="0.1.0")


class AskRequest(BaseModel):
    question: str
    context: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[str] = []


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
