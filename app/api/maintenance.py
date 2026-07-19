"""
Maintenance Intelligence API Routes
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["maintenance"])

_maintenance_service = None

def _get_maintenance_service():
    global _maintenance_service
    if _maintenance_service is None:
        from app.services.maintenance import MaintenanceService
        _maintenance_service = MaintenanceService(storage_dir="storage")
    return _maintenance_service


class WorkOrderCreate(BaseModel):
    equipment_tag: str
    description: str
    priority: str = "medium"


class WorkOrderComplete(BaseModel):
    root_cause: str
    actions: list[str]


@router.get("/maintenance/work-orders")
async def list_work_orders(
    status: Optional[str] = None,
    equipment_tag: Optional[str] = None,
):
    return _get_maintenance_service().get_work_orders(status=status, equipment_tag=equipment_tag)


@router.post("/maintenance/work-orders")
async def create_work_order(order: WorkOrderCreate):
    wo = _get_maintenance_service().create_work_order(order.equipment_tag, order.description, order.priority)
    return vars(wo)


@router.put("/maintenance/work-orders/{wo_id}/complete")
async def complete_work_order(wo_id: str, data: WorkOrderComplete):
    wo = _get_maintenance_service().complete_work_order(wo_id, data.root_cause, data.actions)
    if not wo:
        raise HTTPException(404, f"Work order {wo_id} not found")
    return vars(wo)


@router.get("/maintenance/equipment/{equipment_tag}/health")
async def get_equipment_health(equipment_tag: str):
    health = _get_maintenance_service().get_equipment_health(equipment_tag)
    return {
        "equipment_tag": health.equipment_tag,
        "health_score": health.health_score,
        "failure_probability": health.failure_probability,
        "recommended_actions": health.recommended_actions,
    }


@router.post("/maintenance/rca")
async def analyze_root_cause(problem: str, equipment_tag: str):
    return _get_maintenance_service().analyze_root_cause(problem, equipment_tag)


@router.get("/maintenance/stats")
async def get_maintenance_stats():
    return _get_maintenance_service().get_maintenance_stats()
