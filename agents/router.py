"""Rule-based agent router (Phase 1 — no LLM classification)."""

from __future__ import annotations

from typing import Literal

AgentKind = Literal["code", "docs", "security"]

VALID_AGENTS: frozenset[str] = frozenset({"code", "docs", "security"})

# Scored keyword groups — highest score wins; ties break: security > code > docs
_SECURITY_KEYWORDS = (
    "security",
    "vulnerab",
    "cve",
    "auth",
    "jwt",
    "oauth",
    "token",
    "secret",
    "password",
    "credential",
    "permission",
    "rbac",
    "encrypt",
    "decrypt",
    "xss",
    "injection",
    "csrf",
    "sanitize",
    "privilege",
    "session hijack",
    "exploit",
    "threat",
    "unsafe",
    "hardcoded",
)

_DOCS_KEYWORDS = (
    "readme",
    "document",
    "docs",
    "install",
    "setup",
    "getting started",
    "how do i run",
    "how to run",
    "how to install",
    "configure",
    "configuration",
    "deployment",
    "deploy",
    "usage",
    "tutorial",
    "guide",
    "changelog",
    "license",
    "requirements.txt",
    "env example",
    "quickstart",
)

_CODE_KEYWORDS = (
    "function",
    "class",
    "method",
    "implement",
    "implementation",
    "orchestrat",
    "api endpoint",
    "endpoint",
    "route",
    "handler",
    "source code",
    "codebase",
    "module",
    "import",
    "call graph",
    "symbol",
    "how does",
    "how is",
    "where is",
    "what does",
    "traceback",
    "stack",
    "bug",
    "refactor",
    "algorithm",
)

_TIE_BREAK: dict[AgentKind, int] = {"security": 3, "code": 2, "docs": 1}


def _score(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for kw in keywords if kw in text)


def route_question(
    question: str,
    agent_override: str | None = None,
) -> AgentKind:
    """
    Pick code | docs | security.

    If agent_override is a valid agent name, use it.
    Otherwise score keyword hits; default to code for technical/default ask.
    """
    if agent_override:
        key = agent_override.strip().lower()
        if key in VALID_AGENTS:
            return key  # type: ignore[return-value]
        raise ValueError(
            f"Invalid agent '{agent_override}'. Use one of: code, docs, security"
        )

    text = (question or "").strip().lower()
    if not text:
        return "docs"

    scores: dict[AgentKind, int] = {
        "security": _score(text, _SECURITY_KEYWORDS),
        "docs": _score(text, _DOCS_KEYWORDS),
        "code": _score(text, _CODE_KEYWORDS),
    }

    best = max(scores.values())
    if best == 0:
        # No keyword hit — default to code for repo Q&A
        return "code"

    tied = [k for k, v in scores.items() if v == best]
    return max(tied, key=lambda k: _TIE_BREAK[k])
