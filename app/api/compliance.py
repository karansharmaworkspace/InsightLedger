"""
Compliance Intelligence API Routes
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["compliance"])

_compliance_service = None

def _get_compliance_service():
    global _compliance_service
    if _compliance_service is None:
        from app.services.compliance import ComplianceService
        _compliance_service = ComplianceService(storage_dir="storage")
    return _compliance_service


class ComplianceCheckCreate(BaseModel):
    standard: str
    section: str
    requirement: str


class ComplianceCheckUpdate(BaseModel):
    status: str
    evidence: list[str] = []


class LessonCreate(BaseModel):
    title: str
    description: str
    category: str
    equipment_tags: list[str] = []
    tags: list[str] = []


@router.get("/compliance/checks")
async def list_checks(standard: Optional[str] = None):
    return _get_compliance_service().get_compliance_checks(standard=standard)


@router.post("/compliance/checks")
async def create_check(check: ComplianceCheckCreate):
    return vars(_get_compliance_service().add_compliance_check(check.standard, check.section, check.requirement))


@router.put("/compliance/checks/{check_id}")
async def update_check(check_id: str, data: ComplianceCheckUpdate):
    result = _get_compliance_service().update_check_status(check_id, data.status, data.evidence)
    if not result:
        raise HTTPException(404, f"Check {check_id} not found")
    return vars(result)


@router.get("/compliance/status")
async def get_status(standard: Optional[str] = None):
    return _get_compliance_service().get_compliance_status(standard=standard)


@router.get("/compliance/lessons")
async def list_lessons(category: Optional[str] = None, equipment_tag: Optional[str] = None):
    return _get_compliance_service().get_lessons_learned(category=category, equipment_tag=equipment_tag)


@router.post("/compliance/lessons")
async def create_lesson(lesson: LessonCreate):
    return vars(_get_compliance_service().add_lesson(lesson.title, lesson.description, lesson.category, lesson.equipment_tags, lesson.tags))


@router.get("/compliance/lessons/search")
async def search_lessons(q: str = Query(..., min_length=1)):
    return _get_compliance_service().search_lessons(q)
