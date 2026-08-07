"""Run routed agent: retrieve → agent prompt → LLM."""

from __future__ import annotations

from agents.base import retrieve_config_for
from agents.prompts import build_agent_prompt
from agents.router import AgentKind, route_question
from llm_service import llm_service
from retriever import build_context


def run_ask(
    question: str,
    *,
    extra_context: str | None = None,
    project: str | None = None,
    agent: str | None = None,
) -> dict:
    """
    Route question to code/docs/security, retrieve filtered context, ask LLM.

    Returns dict with agent, answer, sources, project, project_name.
    """
    kind: AgentKind = route_question(question, agent_override=agent)
    cfg = retrieve_config_for(kind)

    context, sources, project_info = build_context(
        question,
        extra_context,
        project=project,
        chunk_type=cfg.chunk_type,
        prefer_security_paths=cfg.prefer_security_paths,
    )

    prompt = build_agent_prompt(kind, question, context)
    answer = llm_service.generate(prompt, model=cfg.model)

    return {
        "agent": kind,
        "model": cfg.model,
        "answer": answer,
        "sources": sources,
        "project": project_info.get("project"),
        "project_name": project_info.get("project_name"),
    }
