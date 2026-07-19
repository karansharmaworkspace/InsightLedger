"""
Vector Search API Routes
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["search"])

_vector_service = None

def _get_vector_service():
    global _vector_service
    if _vector_service is None:
        from app.services.vector_search import VectorSearchService
        _vector_service = VectorSearchService(storage_dir="storage")
    return _vector_service


@router.get("/search/semantic")
async def semantic_search(
    q: str = Query(..., min_length=1),
    n: int = Query(10, ge=1, le=50),
    document_type: Optional[str] = None,
):
    filters = {}
    if document_type:
        filters["content_type"] = document_type

    results = _get_vector_service().search(q, n_results=n, filters=filters if filters else None)

    return {
        "query": q,
        "results": results,
        "count": len(results),
    }


@router.get("/search/document/{document_id}/chunks")
async def get_document_chunks(document_id: str):
    chunks = _get_vector_service().get_document_chunks(document_id)
    return {
        "document_id": document_id,
        "chunks": chunks,
        "count": len(chunks),
    }


@router.get("/search/stats")
async def get_search_stats():
    return _get_vector_service().get_stats()
