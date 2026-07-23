# QA Agent API

Simple FastAPI QA agent powered by Llama (via Ollama), with a local docs knowledge base.

## Structure

```text
qa_agnet/
├── app.py            # FastAPI routes
├── llm_service.py    # LLM communication (Ollama)
├── prompt.py         # Prompt templates
├── retriever.py      # Keyword search over docs/
├── docs/             # Knowledge base (.md files)
├── .env              # OLLAMA_URL + OLLAMA_MODEL
├── requirements.txt
└── README.md
```

| File | Role |
|------|------|
| `app.py` | HTTP endpoints. Auto-retrieves context, then asks LLM. |
| `retriever.py` | Searches `docs/` and builds context for the question. |
| `llm_service.py` | Loads env, builds prompt, calls Ollama. |
| `prompt.py` | Strict QA prompt (no invented CLI/commands). |
| `docs/` | Your knowledge base. Add more `.md` files anytime. |

## How the flow runs

```text
1. Client → POST /ask { "question": "..." }

2. app.py
   - Calls retriever.build_context(question)
   - Optionally merges user-provided context

3. retriever.py
   - Reads docs/*.md
   - Keyword-matches the question
   - Returns top chunks as context + source names

4. llm_service.py + prompt.py
   - Builds a grounded prompt from context
   - Calls Ollama (Llama)

5. Response
   {
     "answer": "...",
     "sources": ["fastapi_basics.md"]
   }
```

```text
Client ──► app.py ──► retriever.py ──► docs/*.md
              │
              └──► llm_service.py ──► prompt.py ──► Ollama
                       │
                       ◄────── answer + sources
```

## Environment

```env
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3.1:8b
```

## Prerequisites

```bash
ollama pull llama3.1:8b
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload
```

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

## Example

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "how do we make new project in fast api"}'
```

Expected: steps using venv + pip + `uvicorn main:app --reload`, with `sources` including `fastapi_basics.md`.

### Optional extra context

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the capital?", "context": "France capital is Paris."}'
```

## Add more knowledge

Create any `.md` file in `docs/`. The retriever picks it up automatically on the next `/ask`.
