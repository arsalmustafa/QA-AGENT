"""Tree-sitter based code chunking (functions / classes / methods)."""

from __future__ import annotations

from pathlib import Path
import re

from ingestion.chunker import chunk_text

# extension -> tree-sitter language name
EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "c_sharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
}

# node types that make good code chunks per language family
SYMBOL_NODE_TYPES = {
    "python": {"function_definition", "class_definition"},
    "javascript": {
        "function_declaration",
        "method_definition",
        "class_declaration",
        "export_statement",
        "lexical_declaration",
    },
    "typescript": {
        "function_declaration",
        "method_definition",
        "class_declaration",
        "export_statement",
        "interface_declaration",
        "type_alias_declaration",
    },
    "tsx": {
        "function_declaration",
        "method_definition",
        "class_declaration",
        "export_statement",
        "interface_declaration",
    },
    "go": {"function_declaration", "method_declaration", "type_declaration"},
    "rust": {"function_item", "impl_item", "struct_item", "enum_item", "mod_item"},
    "java": {"method_declaration", "class_declaration", "interface_declaration"},
    "ruby": {"method", "class", "module"},
    "php": {"function_definition", "class_declaration", "method_declaration"},
    "c": {"function_definition", "struct_specifier", "type_definition"},
    "cpp": {"function_definition", "class_specifier", "struct_specifier"},
    "c_sharp": {"method_declaration", "class_declaration", "interface_declaration"},
    "swift": {"function_declaration", "class_declaration", "struct_declaration"},
    "kotlin": {"function_declaration", "class_declaration", "object_declaration"},
    "scala": {"function_definition", "class_definition", "object_definition"},
}


def language_for_path(path: str) -> str | None:
    suffix = Path(path).suffix.lower()
    name = Path(path).name.lower()
    if name == "dockerfile":
        return None
    return EXT_TO_LANG.get(suffix)


def _safe_id(*parts: str) -> str:
    joined = "-".join(p for p in parts if p)
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", joined).strip("-").lower()[:200] or "chunk"


def _node_name(node, source_bytes: bytes) -> str:
    # Prefer identifier / name / property_identifier child
    for child in node.children:
        if child.type in {
            "identifier",
            "name",
            "property_identifier",
            "type_identifier",
        }:
            return source_bytes[child.start_byte : child.end_byte].decode(
                "utf-8", errors="ignore"
            )
    return node.type


def _collect_symbols(node, language: str, source_bytes: bytes, out: list) -> None:
    targets = SYMBOL_NODE_TYPES.get(language, set())
    if node.type in targets:
        text = source_bytes[node.start_byte : node.end_byte].decode(
            "utf-8", errors="ignore"
        ).strip()
        if text:
            out.append(
                {
                    "symbol": _node_name(node, source_bytes),
                    "kind": node.type,
                    "text": text,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                }
            )
        # Still walk into class bodies for methods
        if node.type in {
            "class_definition",
            "class_declaration",
            "class_specifier",
            "impl_item",
        }:
            for child in node.children:
                _collect_symbols(child, language, source_bytes, out)
        return

    for child in node.children:
        _collect_symbols(child, language, source_bytes, out)


def chunk_code(
    text: str,
    *,
    source: str,
    path: str,
    project: str,
    project_name: str,
    owner: str = "",
    repo: str = "",
    max_chars: int = 2500,
) -> list[dict]:
    """
    Parse code with tree-sitter and emit function/class chunks.
    Falls back to plain text chunking if parse fails or language unknown.
    """
    language = language_for_path(path)
    base_meta = {
        "source": source,
        "path": path,
        "project": project,
        "project_name": project_name,
        "owner": owner,
        "repo": repo,
        "type": "code",
        "language": language or "text",
    }

    if not text.strip():
        return []

    if not language:
        return _fallback_chunks(text, source=source, base_meta=base_meta)

    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(language)
        source_bytes = text.encode("utf-8")
        tree = parser.parse(source_bytes)
        symbols: list[dict] = []
        _collect_symbols(tree.root_node, language, source_bytes, symbols)
    except Exception:
        return _fallback_chunks(text, source=source, base_meta=base_meta)

    if not symbols:
        return _fallback_chunks(text, source=source, base_meta=base_meta)

    chunks: list[dict] = []
    for i, sym in enumerate(symbols):
        body = sym["text"]
        # Split oversized symbols
        pieces = [body] if len(body) <= max_chars else [
            body[start : start + max_chars] for start in range(0, len(body), max_chars)
        ]
        for j, piece in enumerate(pieces):
            chunks.append(
                {
                    "id": _safe_id(
                        project, path, sym["symbol"], str(i), str(j)
                    ),
                    "text": piece,
                    "symbol": sym["symbol"],
                    "kind": sym["kind"],
                    **base_meta,
                }
            )
    return chunks


def _fallback_chunks(text: str, *, source: str, base_meta: dict) -> list[dict]:
    plain = chunk_text(text, source=source)
    out: list[dict] = []
    for item in plain:
        out.append(
            {
                **item,
                "id": _safe_id(base_meta.get("project", ""), item["id"]),
                "symbol": "",
                "kind": "file",
                **base_meta,
                "source": source,
                "text": item["text"],
            }
        )
    return out
