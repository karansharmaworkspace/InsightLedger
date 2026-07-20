"""Document ingestion pipeline for heterogeneous industrial documents.

Supports: PDF (text + scanned), Excel, images (OCR), plain text.
Outputs: structured chunks with metadata for knowledge graph.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pdfplumber
import openpyxl
import easyocr


class DocumentChunk:
    """A single chunk of extracted document content."""

    def __init__(
        self,
        content: str,
        source: str,
        doc_type: str,
        page: int | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.content = content
        self.source = source
        self.doc_type = doc_type
        self.page = page
        self.metadata = metadata or {}
        self.id = self._make_id()

    def _make_id(self) -> str:
        raw = f"{self.source}:{self.page}:{self.content[:200]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "doc_type": self.doc_type,
            "page": self.page,
            "metadata": self.metadata,
        }


class DocumentIngestor:
    """Ingest documents from multiple formats into chunks."""

    def __init__(self):
        self._ocr_reader = None
        self._hindi_ocr_reader = None

    @property
    def ocr(self) -> easyocr.Reader:
        if self._ocr_reader is None:
            self._ocr_reader = easyocr.Reader(["en"], gpu=False)
        return self._ocr_reader

    @property
    def hindi_ocr(self) -> easyocr.Reader:
        """Lazy-load Hindi + English OCR reader."""
        if self._hindi_ocr_reader is None:
            self._hindi_ocr_reader = easyocr.Reader(["hi", "en"], gpu=False)
        return self._hindi_ocr_reader

    def _has_devanagari(self, text: str) -> bool:
        """Check if text contains Devanagari (Hindi) script."""
        for char in text:
            if '\u0900' <= char <= '\u097F':
                return True
        return False

    def ingest(self, file_path: str) -> list[DocumentChunk]:
        path = Path(file_path)
        if not path.exists():
            return []

        ext = path.suffix.lower()
        if ext == ".pdf":
            return self._ingest_pdf(path)
        elif ext in (".xlsx", ".xls"):
            return self._ingest_excel(path)
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            return self._ingest_image(path)
        elif ext in (".txt", ".md", ".csv"):
            return self._ingest_text(path)
        else:
            return []

    def _ingest_pdf(self, path: Path) -> list[DocumentChunk]:
        chunks = []
        try:
            with pdfplumber.open(str(path)) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        chunks.append(DocumentChunk(
                            content=text.strip(),
                            source=str(path),
                            doc_type="pdf",
                            page=i + 1,
                            metadata={"total_pages": len(pdf.pages)},
                        ))

                    # If no text, try OCR on page image
                    if not text.strip():
                        img = page.to_image(resolution=300)
                        tmp_path = tempfile.mktemp(suffix=".png")
                        try:
                            img.save(tmp_path)
                            ocr_text = self._ocr_read(tmp_path)
                            if ocr_text.strip():
                                chunks.append(DocumentChunk(
                                    content=ocr_text.strip(),
                                    source=str(path),
                                    doc_type="pdf_ocr",
                                    page=i + 1,
                                    metadata={"total_pages": len(pdf.pages), "ocr": True},
                                ))
                        finally:
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
        except Exception as e:
            print(f"[INGEST] PDF error: {e}")
        return chunks

    def _ingest_excel(self, path: Path) -> list[DocumentChunk]:
        chunks = []
        try:
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_text = " | ".join(str(c) if c is not None else "" for c in row)
                    if row_text.strip(" |"):
                        rows.append(row_text)
                if rows:
                    content = "\n".join(rows)
                    chunks.append(DocumentChunk(
                        content=content,
                        source=str(path),
                        doc_type="excel",
                        metadata={"sheet": sheet_name, "rows": len(rows)},
                    ))
            wb.close()
        except Exception as e:
            print(f"[INGEST] Excel error: {e}")
        return chunks

    def _ingest_image(self, path: Path) -> list[DocumentChunk]:
        chunks = []
        try:
            text = self._ocr_read(str(path))
            if text.strip():
                chunks.append(DocumentChunk(
                    content=text.strip(),
                    source=str(path),
                    doc_type="image_ocr",
                    metadata={"ocr": True},
                ))
        except Exception as e:
            print(f"[INGEST] Image OCR error: {e}")
        return chunks

    def _ingest_text(self, path: Path) -> list[DocumentChunk]:
        chunks = []
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if text.strip():
                # Split into ~1000 char chunks
                for i in range(0, len(text), 1000):
                    chunk_text = text[i:i + 1000].strip()
                    if chunk_text:
                        chunks.append(DocumentChunk(
                            content=chunk_text,
                            source=str(path),
                            doc_type="text",
                            metadata={"offset": i},
                        ))
        except Exception as e:
            print(f"[INGEST] Text error: {e}")
        return chunks

    def _ocr_read(self, image_path: str) -> str:
        """Read text from image using OCR with Hindi support."""
        # First pass with English to detect script
        results = self.ocr.readtext(image_path)
        initial_text = "\n".join(text for _, text, conf in results if conf > 0.3)

        # If Devanagari detected, re-run with Hindi reader
        if self._has_devanagari(initial_text):
            results = self.hindi_ocr.readtext(image_path)
            return "\n".join(text for _, text, conf in results if conf > 0.3)

        return initial_text


class IngestionManager:
    """Manages batch ingestion of documents."""

    def __init__(self, storage_dir: str | None = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.getcwd(), "storage", "documents")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ingestor = DocumentIngestor()

    def ingest_file(self, file_path: str) -> list[dict[str, Any]]:
        chunks = self.ingestor.ingest(file_path)
        return [c.to_dict() for c in chunks]

    def ingest_directory(self, dir_path: str) -> list[dict[str, Any]]:
        all_chunks = []
        for f in Path(dir_path).rglob("*"):
            if f.is_file() and f.suffix.lower() in (
                ".pdf", ".xlsx", ".xls", ".png", ".jpg", ".jpeg",
                ".bmp", ".tiff", ".txt", ".md", ".csv",
            ):
                chunks = self.ingestor.ingest(str(f))
                all_chunks.extend(c.to_dict() for c in chunks)
        return all_chunks
