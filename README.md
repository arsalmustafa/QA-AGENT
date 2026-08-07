# QA Agent API

FastAPI QA agent with local Ollama + Pinecone.
Upload any new file → saved in `storage/` → text extracted → embedded.

## Structure

```text
qa_agnet/
    ├── app.py                 # /ask , /documents, /repos, /projects
    ├── frontend/              # React (Vite) SPA — separate from API
    ├── agents/                # Phase-1 multi-agent router
│   ├── router.py          # rules → code | docs | security
│   ├── prompts.py
│   ├── base.py            # per-agent retrieval config
│   └── runner.py          # retrieve → prompt → LLM
├── llm_service.py
├── prompt.py              # legacy single QA prompt (still used by llm_service.ask)
├── embeddings.py
├── pinecone_client.py
├── retriever.py           # Pinecone + type / security-path filters
├── reranker.py            # Hybrid BM25 + vector rerank (top 10 → best 3)
├── github_repos.py        # GitHub API ingest (no clone)
├── project_catalog.py
├── ingestion/
│   ├── code_chunker.py    # tree-sitter functions/classes
│   ├── file_handler.py
│   ├── chunker.py         # doc/pdf text chunks
│   ├── store.py           # Pinecone upsert + project metadata
│   └── service.py
├── storage/               # uploaded files + projects catalogs
├── postman/               # Postman collection for QA
│   ├── QA_Agent_API.postman_collection.json
│   └── README.md
├── .env
└── requirements.txt
```

## Frontend (React)

Separate SPA in `frontend/` (Vite + React + TypeScript).

```bash
# terminal 1 — API
source .venv/bin/activate
uvicorn app:app --reload

# terminal 2 — UI
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 → **Continue with GitHub**.

Root `.env` should include:

```env
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

After OAuth, the API redirects to `/auth/callback?token=…&refresh_token=…` on the SPA.  
The SPA stores both tokens and **auto-refreshes** the access token via `POST /auth/refresh`  
(before expiry, and once on 401). Default access TTL is 60 minutes; refresh lasts 30 days.

Postman can still get JSON by calling the callback with `format=json`.

See `frontend/README.md` for routes and details.

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

## Ingest GitHub repo (no clone + tree-sitter)

Uses **PyGithub** + **tree-sitter** (many languages). Nothing is `git clone`d.

1. Login: http://127.0.0.1:8000/auth/github  
2. Ingest project:

```bash
curl -X POST http://127.0.0.1:8000/repos/ingest \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"owner": "octocat", "repo": "Hello-World"}'
```

Code files are split into functions/classes and stored in Pinecone with:
`project = "owner/repo"`, `path`, `symbol`, `language`.

A **folders/files catalog** is also saved at:
`storage/projects/{owner}__{repo}.json`

### Project catalog

```bash
# List projects
curl http://127.0.0.1:8000/projects \
  -H "Authorization: Bearer YOUR_JWT"

# Get one project map
curl http://127.0.0.1:8000/projects/octocat/Hello-World \
  -H "Authorization: Bearer YOUR_JWT"
```

Example catalog shape:

```json
{
  "project": "octocat/Hello-World",
  "project_name": "Hello-World",
  "folders": ["src", "tests"],
  "files": [
    {
      "name": "auth.py",
      "path": "src/auth.py",
      "type": "code",
      "language": "python",
      "symbols": ["authenticate_user"]
    },
    {
      "name": "README.md",
      "path": "README.md",
      "type": "documentation",
      "language": "markdown"
    }
  ]
}
```

### Ask about a specific project

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"question": "How does login work?", "project": "octocat/Hello-World"}'
```

Response:

```json
{
  "agent": "code",
  "model": "qwen2.5-coder:7b",
  "project": "octocat/Hello-World",
  "project_name": "Hello-World",
  "answer": "...",
  "sources": ["octocat/Hello-World:auth/login.py"]
}
```

Omit `project` to search all docs + repos (previous behavior).

### Multi-agent ask (Phase 1)

`POST /ask` routes each question to one of:

| Agent | Retrieval | Model (default) | Focus |
|-------|-----------|-----------------|--------|
| `code` | Pinecone `type=code` | `OLLAMA_CODE_MODEL` (`qwen2.5-coder:7b`) | Functions, APIs, control flow |
| `docs` | Pinecone `type=doc` | `OLLAMA_MODEL` (`llama3.1:8b`) | Setup, README, how-to |
| `security` | Broader search, prefer auth/security paths | `OLLAMA_MODEL` | Auth, secrets, risks (grounded only) |

Routing is **rule-based** (keywords). Force an agent with `"agent": "code"|"docs"|"security"`.

Pull models once:

```bash
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
```

```bash
# Auto-route
curl -X POST http://127.0.0.1:8000/ask \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"question": "Are JWT secrets handled safely?", "project": "octocat/Hello-World"}'

# Force docs agent
curl -X POST http://127.0.0.1:8000/ask \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I install this?", "project": "octocat/Hello-World", "agent": "docs"}'
```

Postgres / Graph DB are **not** in Phase 1.

## Postman

Import the ready-made collection:

```text
postman/
├── QA_Agent_API.postman_collection.json
└── README.md
```

1. Postman → **Import** → `postman/QA_Agent_API.postman_collection.json`
2. Collection → **Variables** → set `base_url` if needed  
3. Run **1. Auth → Start OAuth**, open `authorize_url` in a browser, then paste `access_token` into `token` (or use **Callback** with `oauth_code`)
3. `base_url` defaults to `http://127.0.0.1:8000`

Folders: Health, Auth, Projects, Ingest, Ask (multi-agent).

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
  1. Agent router → code | docs | security
  2. Embed question (Ollama)
  3. Pinecone retrieve (project + type / path filters) top 10
  4. Rerank (vector + BM25 hybrid) → keep best 3
  5. Agent prompt + Llama answer
```

Config in `.env`:
```env
RETRIEVE_TOP_K=10
RERANK_TOP_N=3
```

## Ask

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"question": "your question", "project": "owner/repo"}'
```

## Supported types

`.pdf`, `.txt`, `.md`, `.markdown`, `.csv`, `.json`, `.log`

## Re-ingest everything in storage/

```bash
python -m ingestion
```
