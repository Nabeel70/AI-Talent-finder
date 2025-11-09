from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from parsing import extract_text_from_docx, extract_text_from_pdf, extract_text_from_txt


@dataclass
class SourceDocument:
    """Container for any piece of evidence used to build a skill profile."""

    name: str
    kind: str
    text: str
    visibility: str = "private"  # either "private" or "public"
    origin: str = "manual"  # "manual" or "upload"
    metadata: Optional[dict] = None

    @property
    def word_count(self) -> int:
        return len(self.text.split())


SUPPORTED_SUFFIXES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "txt",
}


def _read_upload(upload, suffix: str) -> str:
    """Read bytes from an uploaded file based on suffix."""
    upload.seek(0)
    if suffix == ".pdf":
        return extract_text_from_pdf(upload)
    if suffix == ".docx":
        return extract_text_from_docx(upload)
    if suffix in {".txt", ".md"}:
        return extract_text_from_txt(upload)
    raise ValueError(f"Unsupported file type: {suffix}")


def source_from_upload(upload, kind: str, visibility: str = "private") -> SourceDocument:
    """Create a SourceDocument from a Streamlit upload object."""
    suffix = Path(upload.name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported upload type: {upload.name}")
    text = _read_upload(upload, suffix)
    return SourceDocument(
        name=upload.name,
        kind=kind,
        text=text.strip(),
        visibility=visibility,
        origin="upload",
    )


def source_from_text(
    name: str,
    text: str,
    kind: str,
    visibility: str = "private",
    metadata: Optional[dict] = None,
) -> Optional[SourceDocument]:
    """Create a SourceDocument from free-form text."""
    if not text:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    return SourceDocument(
        name=name,
        kind=kind,
        text=cleaned,
        visibility=visibility,
        origin="manual",
        metadata=metadata or {},
    )


def merge_sources_text(sources: Iterable[SourceDocument], visibility: Optional[str] = None) -> str:
    """Merge multiple sources into a single blob of text."""
    sections: List[str] = []
    for src in sources:
        if visibility and src.visibility != visibility:
            continue
        if not src.text.strip():
            continue
        sections.append(f"[{src.name} | {src.kind}]\n{src.text.strip()}")
    return "\n\n".join(sections)


def describe_sources(sources: Iterable[SourceDocument]) -> dict:
    """Return quick stats about loaded sources."""
    sources = list(sources)
    by_kind = Counter(src.kind for src in sources)
    visibility = Counter(src.visibility for src in sources)
    total_words = sum(src.word_count for src in sources)
    return {
        "count": len(sources),
        "by_kind": dict(by_kind),
        "visibility": dict(visibility),
        "total_words": total_words,
        "avg_words": round(total_words / len(sources), 1) if sources else 0,
    }
