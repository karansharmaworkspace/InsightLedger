"""
Document Ingestion Service
Handles PDF text/table extraction, spreadsheet processing, and OKF bundle storage.
"""
import os
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

import pdfplumber
import pandas as pd
import tempfile
from fastapi import UploadFile

from app.services.ocr_scanned import ScannedDocumentOCR
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.vector_search import VectorSearchService


@dataclass
class ExtractedContent:
    """Structured output from document extraction."""
    document_id: str
    filename: str
    file_type: str
    file_hash: str
    text: str
    tables: List[List[Dict[str, str]]]
    metadata: Dict[str, Any]
    page_count: int
    status: str  # pending, processing, completed, failed
    error: Optional[str] = None


class DocumentIngestionService:
    """Service for ingesting PDF and spreadsheet documents."""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_service = ScannedDocumentOCR()
        self.kg_service = KnowledgeGraphService(storage_dir)
        self.vector_service = VectorSearchService(storage_dir)

    def compute_file_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    async def extract_pdf(self, file: UploadFile) -> ExtractedContent:
        """Extract text, tables, and metadata from PDF."""
        content = await file.read()
        file_hash = self.compute_file_hash(content)
        doc_id = file_hash[:12]

        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            is_scanned = self.ocr_service.is_scanned_pdf(tmp_path)

            if is_scanned:
                ocr_result = self.ocr_service.ocr_pdf(tmp_path, doc_id, file.filename)
                os.unlink(tmp_path)

                return ExtractedContent(
                    document_id=doc_id,
                    filename=file.filename,
                    file_type="pdf",
                    file_hash=file_hash,
                    text=ocr_result.text,
                    tables=[],
                    metadata={
                        "is_scanned": True,
                        "ocr_confidence": ocr_result.confidence,
                        "page_count": ocr_result.page_count,
                        "processing_time": ocr_result.processing_time,
                        "extracted_at": datetime.now().isoformat(),
                    },
                    page_count=ocr_result.page_count,
                    status="completed",
                )

            with pdfplumber.open(tmp_path) as pdf:
                text_parts = []
                tables = []

                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            if len(table) > 1:
                                headers = [str(h) if h else f"col_{i}" for i, h in enumerate(table[0])]
                                for row in table[1:]:
                                    row_dict = {headers[i]: str(cell) if cell else "" for i, cell in enumerate(row)}
                                    tables.append([row_dict])
                            else:
                                tables.append([{"raw": str(row)} for row in table])

                metadata = pdf.metadata or {}
                metadata.update({
                    "is_scanned": False,
                    "page_count": len(pdf.pages),
                    "extracted_at": datetime.now().isoformat(),
                })

                os.unlink(tmp_path)

                return ExtractedContent(
                    document_id=doc_id,
                    filename=file.filename,
                    file_type="pdf",
                    file_hash=file_hash,
                    text="\n\n".join(text_parts),
                    tables=tables,
                    metadata=metadata,
                    page_count=len(pdf.pages),
                    status="completed",
                )

        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return ExtractedContent(
                document_id=doc_id,
                filename=file.filename,
                file_type="pdf",
                file_hash=file_hash,
                text="",
                tables=[],
                metadata={},
                page_count=0,
                status="failed",
                error=str(e),
            )

    async def extract_excel(self, file: UploadFile) -> ExtractedContent:
        """Extract data from Excel files."""
        content = await file.read()
        file_hash = self.compute_file_hash(content)
        doc_id = file_hash[:12]

        try:
            # Save temp file for pandas
            temp_path = self.storage_dir / f"temp_{doc_id}.xlsx"
            temp_path.write_bytes(content)

            df = pd.read_excel(temp_path, sheet_name=None)
            temp_path.unlink()

            all_text = []
            all_tables = []
            sheet_count = len(df)

            for sheet_name, sheet_df in df.items():
                all_text.append(f"## Sheet: {sheet_name}")
                all_text.append(sheet_df.to_string(index=False))

                # Convert to list of dicts
                table_data = sheet_df.fillna("").to_dict(orient="records")
                all_tables.append(table_data)

            metadata = {
                "sheet_count": sheet_count,
                "sheets": list(df.keys()),
                "extracted_at": datetime.now().isoformat(),
            }

            return ExtractedContent(
                document_id=doc_id,
                filename=file.filename,
                file_type="xlsx",
                file_hash=file_hash,
                text="\n\n".join(all_text),
                tables=all_tables,
                metadata=metadata,
                page_count=sheet_count,
                status="completed",
            )

        except Exception as e:
            return ExtractedContent(
                document_id=doc_id,
                filename=file.filename,
                file_type="xlsx",
                file_hash=file_hash,
                text="",
                tables=[],
                metadata={},
                page_count=0,
                status="failed",
                error=str(e),
            )

    async def extract_csv(self, file: UploadFile) -> ExtractedContent:
        """Extract data from CSV files."""
        content = await file.read()
        file_hash = self.compute_file_hash(content)
        doc_id = file_hash[:12]

        try:
            temp_path = self.storage_dir / f"temp_{doc_id}.csv"
            temp_path.write_bytes(content)

            df = pd.read_csv(temp_path)
            temp_path.unlink()

            text = df.to_string(index=False)
            table_data = df.fillna("").to_dict(orient="records")

            metadata = {
                "columns": list(df.columns),
                "row_count": len(df),
                "extracted_at": datetime.now().isoformat(),
            }

            return ExtractedContent(
                document_id=doc_id,
                filename=file.filename,
                file_type="csv",
                file_hash=file_hash,
                text=text,
                tables=[table_data],
                metadata=metadata,
                page_count=1,
                status="completed",
            )

        except Exception as e:
            return ExtractedContent(
                document_id=doc_id,
                filename=file.filename,
                file_type="csv",
                file_hash=file_hash,
                text="",
                tables=[],
                metadata={},
                page_count=0,
                status="failed",
                error=str(e),
            )

    async def ingest(self, file: UploadFile) -> ExtractedContent:
        """Route to appropriate extractor based on file type."""
        filename = file.filename.lower()

        if filename.endswith(".pdf"):
            return await self.extract_pdf(file)
        elif filename.endswith((".xlsx", ".xls")):
            return await self.extract_excel(file)
        elif filename.endswith(".csv"):
            return await self.extract_csv(file)
        else:
            raise ValueError(f"Unsupported file type: {file.filename}")

    def save_okf_bundle(self, content: ExtractedContent) -> Path:
        """Save extracted content as OKF bundle."""
        bundle_dir = self.storage_dir / "bundles" / content.document_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

        (bundle_dir / "content.md").write_text(content.text, encoding="utf-8")

        (bundle_dir / "tables.json").write_text(
            json.dumps(content.tables, indent=2, default=str),
            encoding="utf-8"
        )

        (bundle_dir / "metadata.json").write_text(
            json.dumps(content.metadata, indent=2, default=str),
            encoding="utf-8"
        )

        manifest = {
            "document_id": content.document_id,
            "filename": content.filename,
            "file_type": content.file_type,
            "file_hash": content.file_hash,
            "status": content.status,
            "created_at": datetime.now().isoformat(),
        }
        (bundle_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        if content.text and content.status == "completed":
            try:
                kg_stats = self.kg_service.process_document(content.text, content.document_id)
                (bundle_dir / "entities.json").write_text(
                    json.dumps(kg_stats, indent=2),
                    encoding="utf-8"
                )
            except Exception:
                pass

            try:
                self.vector_service.index_document(
                    document_id=content.document_id,
                    text=content.text,
                    metadata={
                        "filename": content.filename,
                        "file_type": content.file_type,
                    },
                    tables=content.tables,
                )
            except Exception:
                pass

        return bundle_dir
