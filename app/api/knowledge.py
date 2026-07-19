"""
Knowledge Graph API Routes
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["knowledge"])

_kg_service = None

def _get_kg_service():
    global _kg_service
    if _kg_service is None:
        from app.services.knowledge_graph import KnowledgeGraphService
        _kg_service = KnowledgeGraphService(storage_dir="storage")
    return _kg_service


@router.get("/knowledge-graph")
async def get_knowledge_graph():
    return _get_kg_service().to_json()


@router.get("/knowledge-graph/stats")
async def get_stats():
    return _get_kg_service().get_stats()


@router.get("/equipment")
async def list_equipment():
    return _get_kg_service().get_equipment()


@router.get("/equipment/{equipment_id}")
async def get_equipment(equipment_id: str):
    svc = _get_kg_service()
    equipment = svc.get_equipment(equipment_id)
    if not equipment:
        raise HTTPException(404, f"Equipment {equipment_id} not found")

    node_id = f"equipment:{equipment_id.lower()}"
    connections = svc.get_connected(node_id)

    return {
        "equipment": equipment[0],
        "connections": connections,
    }


@router.get("/search")
async def search_knowledge_graph(q: str = Query(..., min_length=1)):
    results = _get_kg_service().search(q)
    return {"query": q, "results": results, "count": len(results)}
