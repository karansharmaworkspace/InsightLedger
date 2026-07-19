"""
Document Ingestion API Routes
"""
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["ingestion"])

_ingestion_service = None

def _get_ingestion_service():
    global _ingestion_service
    if _ingestion_service is None:
        from app.services.document_ingestion import DocumentIngestionService
        _ingestion_service = DocumentIngestionService(storage_dir="storage")
    return _ingestion_service


@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Ingest a single document (PDF, Excel, or CSV)."""
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    # Check file type
    allowed_extensions = (".pdf", ".xlsx", ".xls", ".csv")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            400,
            f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        svc = _get_ingestion_service()
        result = await svc.ingest(file)
        bundle_path = svc.save_okf_bundle(result)

        return JSONResponse({
            "document_id": result.document_id,
            "filename": result.filename,
            "file_type": result.file_type,
            "status": result.status,
            "page_count": result.page_count,
            "text_length": len(result.text),
            "tables_found": len(result.tables),
            "bundle_path": str(bundle_path),
        })

    except Exception as e:
        raise HTTPException(500, f"Ingestion failed: {str(e)}")


@router.post("/ingest/batch")
async def ingest_batch(files: List[UploadFile] = File(...)):
    """Ingest multiple documents at once."""
    if not files:
        raise HTTPException(400, "No files provided")

    results = []
    svc = _get_ingestion_service()
    for file in files:
        try:
            result = await svc.ingest(file)
            svc.save_okf_bundle(result)
            results.append({
                "filename": file.filename,
                "document_id": result.document_id,
                "status": result.status,
                "error": result.error,
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e),
            })

    success_count = sum(1 for r in results if r["status"] == "completed")
    return JSONResponse({
        "total": len(files),
        "success": success_count,
        "failed": len(files) - success_count,
        "results": results,
    })


@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    svc = _get_ingestion_service()
    bundle_path = svc.storage_dir / "bundles" / document_id

    if not bundle_path.exists():
        raise HTTPException(404, f"Document {document_id} not found")

    # Read manifest
    manifest_path = bundle_path / "manifest.json"
    if manifest_path.exists():
        import json
        manifest = json.loads(manifest_path.read_text())
        return manifest

    raise HTTPException(404, "Document manifest not found")
