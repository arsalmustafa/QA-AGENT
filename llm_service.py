import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from prompt import build_qa_prompt

# Always load .env from this project folder (next to this file)
load_dotenv(Path(__file__).resolve().parent / ".env")

OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

if not OLLAMA_URL or not OLLAMA_MODEL:
    raise RuntimeError(
        "Missing OLLAMA_URL or OLLAMA_MODEL. Set them in the .env file."
    )


class LLMService:
    """Handles communication with the local Llama model via Ollama."""

    def __init__(self, url: str = OLLAMA_URL, model: str = OLLAMA_MODEL):
        self.url = url
        self.model = model

    def ask(self, question: str, context: str | None = None) -> str:
        prompt = build_qa_prompt(question, context)
        return self._generate(prompt)

    def _generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 256,
            },
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(self.url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()


llm_service = LLMService()
