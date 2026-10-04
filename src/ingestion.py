"""Document parsing and chunking for PDF and Markdown files."""
from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from pypdf import PdfReader

from .config import settings
from .guardrails import is_suspicious

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class IngestResult:
    source: str
    chunks: list[Chunk]
    quarantined: int = 0   # chunks withheld because they looked like prompt injection


def _parse_pdf(data: bytes) -> list[tuple[int, str]]:
    """Return [(page_number, text)] (1-indexed)."""
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported.")
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((i, text))
    return pages


def _parse_text(data: bytes) -> list[tuple[int, str]]:
    # page=0 means "not paginated" (Markdown/plain text)
    return [(0, data.decode("utf-8", errors="replace"))]


def _make_splitter(is_markdown: bool) -> RecursiveCharacterTextSplitter:
    kwargs = dict(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    if is_markdown:
        # Splits on headings/code fences/paragraphs before falling back to characters.
        return RecursiveCharacterTextSplitter.from_language(Language.MARKDOWN, **kwargs)
    return RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " ", ""], **kwargs
    )


def ingest_file(filename: str, data: bytes) -> IngestResult:
    """Parse → scan → chunk a single uploaded file."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"File exceeds {settings.max_upload_mb} MB limit.")

    pages = _parse_pdf(data) if ext == ".pdf" else _parse_text(data)
    if not pages:
        raise ValueError("No extractable text found (scanned PDF? OCR is not included).")

    doc_hash = hashlib.sha256(data).hexdigest()[:16]
    splitter = _make_splitter(ext in {".md", ".markdown"})

    chunks: list[Chunk] = []
    quarantined = 0
    for page_no, page_text in pages:
        for idx, text in enumerate(splitter.split_text(page_text)):
            text = text.strip()
            if len(text) < settings.min_chunk_chars:
                continue
            if settings.quarantine_suspicious_chunks and is_suspicious(text):
                quarantined += 1
                log.warning("Quarantined suspicious chunk from %s p.%s", filename, page_no)
                continue
            # Deterministic ID → re-uploading the same file is an idempotent upsert.
            cid = hashlib.sha1(f"{doc_hash}:{page_no}:{idx}".encode()).hexdigest()
            chunks.append(
                Chunk(
                    id=cid,
                    text=text,
                    metadata={
                        "source": filename,
                        "page": page_no,
                        "chunk_index": idx,
                        "doc_hash": doc_hash,
                    },
                )
            )
    return IngestResult(source=filename, chunks=chunks, quarantined=quarantined)
