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
├── github_repos.py        # Read repos via GitHub API (no clone)
├── auth/                  # GitHub OAuth + JWT
│   ├── router.py          # /auth/github, /callback, /me
│   ├── deps.py            # get_current_user
│   ├── jwt_utils.py
│   └── config.py
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

## GitHub OAuth

1. Create an OAuth App on GitHub (Developer settings → OAuth Apps)
2. Callback URL: `http://127.0.0.1:8000/auth/github/callback`
3. Put Client ID / Secret into `.env`:

```env
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_REDIRECT_URI=http://127.0.0.1:8000/auth/github/callback
JWT_SECRET=long-random-string
```

4. Login in browser: http://127.0.0.1:8000/auth/github  
5. Copy `access_token` from the callback JSON into `.env`:

```env
QA_ACCESS_TOKEN=eyJ...
```

`QA_ACCESS_TOKEN` is for local/Postman use only — the API still expects `Authorization: Bearer <token>` on each request. Tokens expire after `JWT_EXPIRE_MINUTES` (default 24h); re-login and update `.env` when expired.

Protected routes: `POST /ask`, `POST /documents`, `POST /repos/ingest`, `GET /auth/me`

## Ingest GitHub repo (no clone)

Uses **PyGithub** + GitHub Contents/Tree API. Nothing is `git clone`d.

1. Re-login (scope now includes `repo`): http://127.0.0.1:8000/auth/github  
2. Call:

```bash
curl -X POST http://127.0.0.1:8000/repos/ingest \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"owner": "octocat", "repo": "Hello-World", "branch": "master"}'
```

Optional: `"path_prefix": "docs/"` to only ingest a folder.

Flow:
```text
POST /repos/ingest
  → GitHub API list tree
  → fetch file contents
  → save text copies to storage/
  → chunk + embed → Pinecone
```

## Postman

Create an environment (e.g. `QA Agent Local`) with:

| Variable | Initial value |
|---|---|
| `base_url` | `http://127.0.0.1:8000` |
| `token` | paste value of `QA_ACCESS_TOKEN` from `.env` |

Then create these requests (Auth → Bearer Token → `{{token}}`):

1. **Me** — `GET {{base_url}}/auth/me`
2. **Upload** — `POST {{base_url}}/documents`  
   Body → form-data → key `file` (type File) → choose a `.md` / `.pdf` / etc.
3. **Ingest repo** — `POST {{base_url}}/repos/ingest`  
   Body → raw JSON:

```json
{
  "owner": "octocat",
  "repo": "Hello-World",
  "branch": "master"
}
```

4. **Ask** — `POST {{base_url}}/ask`  
   Body → raw JSON:

```json
{
  "question": "How do I run and test the Lavni scheduling agent?"
}
```

Or with curl:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"question": "your question"}'
```

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
