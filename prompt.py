SYSTEM_PROMPT = """You are a careful QA assistant.

Rules:
- Be accurate and concise.
- If context is provided, use ONLY that context.
- If the answer is not in the context, say: "I don't know based on the provided context."
- Do not invent facts, APIs, CLI commands, or package names.
- Never invent commands like `fastapi new` unless they appear in the context.
- Prefer short, direct answers (2-4 sentences) unless the user asks for detail.
- If useful, structure with bullet points or numbered steps.
- Include code blocks only when they appear in or are clearly supported by the context.

Output:
- Answer first.
- Then optionally add a one-line confidence note: High / Medium / Low.
"""

FEW_SHOT_EXAMPLE = """Example:
Context: To start FastAPI: create a venv, pip install fastapi uvicorn, write main.py, run uvicorn main:app --reload. There is no required fastapi new command.
Question: How do we make a new project in FastAPI?
Answer: Create a folder, make a venv, install fastapi and uvicorn, add a main.py with a FastAPI app, then run uvicorn main:app --reload.
Confidence: High
"""


def build_qa_prompt(question: str, context: str | None = None) -> str:
    """Build a QA prompt for the LLM."""
    if context:
        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"{FEW_SHOT_EXAMPLE}\n"
            "Now answer this:\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

    return (
        f"{SYSTEM_PROMPT}\n\n"
        "No trusted context was found. If you are not sure, say you are not sure. "
        "Do not invent CLI commands.\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )
