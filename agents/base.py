"""Shared retrieval + model settings per agent."""

from __future__ import annotations

from dataclasses import dataclass

from agents.router import AgentKind
from llm_service import OLLAMA_CODE_MODEL, OLLAMA_MODEL


@dataclass(frozen=True)
class AgentRetrieveConfig:
    chunk_type: str | None = None
    prefer_security_paths: bool = False
    model: str = OLLAMA_MODEL


_CONFIGS: dict[AgentKind, AgentRetrieveConfig] = {
    "code": AgentRetrieveConfig(
        chunk_type="code",
        model=OLLAMA_CODE_MODEL,
    ),
    "docs": AgentRetrieveConfig(chunk_type="doc", model=OLLAMA_MODEL),
    "security": AgentRetrieveConfig(
        chunk_type=None,  # code + docs; narrow by path hints
        prefer_security_paths=True,
        model=OLLAMA_MODEL,
    ),
}


def retrieve_config_for(agent: AgentKind) -> AgentRetrieveConfig:
    return _CONFIGS[agent]
