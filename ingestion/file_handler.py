"""Extract plain text from uploaded / local files (pdf, md, txt, etc.)."""

from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".csv", ".json", ".log"}


class UnsupportedFileTypeError(ValueError):
    pass


def extract_text(path: Path) -> str:
    """Convert a file into plain text for embedding."""
    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if suffix == ".pdf":
        return _extract_pdf(path)

    # Text-like formats
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages).strip()
