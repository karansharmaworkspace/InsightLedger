"""
RAG Query API Routes
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["query"])

_rag_engine = None

def _get_rag_engine():
    global _rag_engine
    if _rag_engine is None:
        from app.services.rag_engine import RAGEngine
        _rag_engine = RAGEngine(storage_dir="storage")
    return _rag_engine


@router.get("/query")
async def query_knowledge_base(
    q: str = Query(..., min_length=1),
    use_cache: bool = Query(True),
):
    result = _get_rag_engine().query(q, use_cache=use_cache)
    return result


@router.get("/query/cache/stats")
async def get_cache_stats():
    return _get_rag_engine().get_cache_stats()
