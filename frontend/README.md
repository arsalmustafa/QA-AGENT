# QA Agent Frontend

React (Vite + TypeScript) UI for the QA Agent API.

## Setup

```bash
cd frontend
cp .env.example .env   # optional — defaults already point at local API
npm install
npm run dev
```

App: http://localhost:5173  
API: http://127.0.0.1:8000

## Backend env for SPA login

In the repo root `.env`:

```env
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GITHUB_REDIRECT_URI=http://127.0.0.1:8000/auth/github/callback
```

OAuth still callbacks to the **API**. After login the API redirects to:

`http://localhost:5173/auth/callback?token=<jwt>&refresh_token=<jwt>`

The SPA stores both and refreshes the access token automatically (`POST /auth/refresh`)  
when it is about to expire (or once after a 401).

For Postman, call the callback with `format=json` to keep the JSON token response.

## Pages

| Route | Purpose |
|-------|---------|
| `/login` | GitHub OAuth |
| `/auth/callback` | Stores JWT from redirect |
| `/` | Project list |
| `/projects/:owner/:repo` | Catalog explorer |
| `/ask` | Multi-agent Q&A |
| `/ingest` | GitHub repo ingest |
| `/upload` | Document upload |

## Scripts

```bash
npm run dev      # Vite dev server
npm run build    # production build
npm run preview  # preview build
```
