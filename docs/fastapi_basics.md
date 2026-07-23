# FastAPI Basics

## What is FastAPI?

FastAPI is a modern Python web framework for building APIs. It is fast, uses type hints, and gives automatic interactive docs at `/docs`.

## How to create a new FastAPI project

There is no required `fastapi new` command for a basic project. Create it manually:

1. Create a folder and virtual environment:

```bash
mkdir myproject
cd myproject
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install fastapi uvicorn
```

3. Create `main.py`:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}
```

4. Run the server:

```bash
uvicorn main:app --reload
```

5. Open:
- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

## Important notes

- Do not invent CLI commands like `fastapi new myproject` unless you are using an official FastAPI tooling that you know exists.
- The common beginner path is: venv → pip install fastapi uvicorn → write `main.py` → run `uvicorn main:app --reload`.
- `app` in `uvicorn main:app` means: module `main.py`, variable named `app`.
