# QA Agent API

FastAPI QA agent with local Ollama + Pinecone.
Upload any new file → saved in `storage/` → text extracted → embedded.

## Structure

```text
qa_agnet/
├── app.py                 # /ask , /documents
├── llm_service.py
├── prompt.py
├── embeddings.py
├── pinecone_client.py
├── retriever.py
├── reranker.py            # Hybrid BM25 + vector rerank (top 10 → best 3)
├── ingestion/
│   ├── file_handler.py    # pdf/md/txt → text
│   ├── chunker.py
│   ├── store.py           # Pinecone upsert
│   └── service.py         # save to storage → process
├── storage/               # ONLY place uploaded files are kept
├── .env
└── requirements.txt
```

## Independent upload flow

```text
POST /documents
  1. Save file into storage/     ← always (no dependency)
  2. Extract text
  3. Embed + Pinecone            ← if key is set
```

Nothing depends on old `docs/` files. Each upload is a new file into `storage/`.

## Run

```bash
source .venv/bin/activate
uvicorn app:app --reload
```

## Upload latest file

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -F "file=@./myfile.pdf"
```

Response example:
```json
{
  "message": "File saved to storage and ingested into Pinecone.",
  "filename": "a1b2c3d4_myfile.pdf",
  "path": ".../storage/a1b2c3d4_myfile.pdf",
  "saved": true,
  "pinecone": true,
  "chunks": 4,
  "chars": 1200
}
```

## Ask flow

```text
POST /ask
  1. Embed question (Ollama)
  2. Pinecone retrieve top 10
  3. Rerank (vector + BM25 hybrid) → keep best 3
  4. Llama answers from those chunks
```

Config in `.env`:
```env
RETRIEVE_TOP_K=10
RERANK_TOP_N=3
```

## Ask

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "your question"}'
```

## Supported types

`.pdf`, `.txt`, `.md`, `.markdown`, `.csv`, `.json`, `.log`

## Re-ingest everything in storage/

```bash
python -m ingestion
```
