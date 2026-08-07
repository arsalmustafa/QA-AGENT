# Postman

## Files

```text
postman/
├── QA_Agent_API.postman_collection.json
└── README.md
```

## Import

1. Postman → **Import** → `postman/QA_Agent_API.postman_collection.json`
2. Collection → **Variables**
3. Set `base_url` if needed (default `http://127.0.0.1:8000`)
4. Leave `token` empty until login

## Login (Postman-friendly)

### Option A — Callback in Postman (recommended)

1. Run **1. Auth → Start OAuth**  
   - Saves `oauth_state` + `authorize_url` automatically  
2. Open `authorize_url` from the response (or Variables) in a **browser** and approve GitHub  
3. After redirect, look at the browser URL:
   `http://127.0.0.1:8000/auth/github/callback?code=....&state=....`  
   - If the page already shows JSON with `access_token` → paste it into collection variable `token`  
   - Or copy only the `code` value into variable `oauth_code`, then run **1. Auth → Callback**  
4. Callback **Tests** script saves `access_token` → `token`  
5. Run **Me** to verify (expect 200 + your GitHub login)

### Option B — Browser + React SPA

1. Open the React app at http://localhost:5173 and use **Continue with GitHub**  
2. Or open `{{base_url}}/auth/github` — after login the API redirects to the SPA with `?token=`  
3. For Postman without the SPA: call callback with `format=json` and copy `access_token`

Protected requests use **Bearer {{token}}** from the collection.

## Collection variables

| Variable | Purpose |
|----------|---------|
| `base_url` | API host |
| `token` | JWT for protected routes |
| `authorize_url` | Set by Start OAuth |
| `oauth_state` | Set by Start OAuth |
| `oauth_code` | Paste from GitHub redirect URL |

## Folders

| Folder | Purpose |
|--------|---------|
| `0. Health` | Health + root |
| `1. Auth` | Start OAuth, Callback, Me |
| `2. Projects` | List / get catalogs |
| `3. Ingest` | Repo ingest + document upload |
| `4. Ask` | Multi-agent ask (code / docs / security) |
