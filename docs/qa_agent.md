# QA Agent Project Notes

## Project structure

```text
qa_agnet/
├── app.py            # FastAPI routes
├── llm_service.py    # Talks to Ollama / Llama
├── prompt.py         # Prompt templates
├── retriever.py      # Finds relevant docs for a question
├── docs/             # Knowledge base (markdown files)
├── .env              # OLLAMA_URL and OLLAMA_MODEL
└── requirements.txt
```

## Ask flow

1. Client sends `POST /ask` with a question.
2. `retriever.py` searches `docs/` for related text.
3. Retrieved text becomes context for the LLM.
4. `llm_service.py` sends prompt + context to Ollama.
5. API returns the answer (and sources used).

## Environment

```env
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3.1:8b
```
