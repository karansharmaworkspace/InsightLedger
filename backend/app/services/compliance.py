"""
Compliance Intelligence Service
Regulatory compliance tracking and lessons learned.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ComplianceCheck:
    id: str
    standard: str
    section: str
    requirement: str
    status: str  # compliant, non_compliant, pending
    evidence: List[str] = field(default_factory=list)
    last_checked: str = ""
    next_check: str = ""


@dataclass
class LessonLearned:
    id: str
    title: str
    description: str
    category: str  # maintenance, safety, operational
    equipment_tags: List[str] = field(default_factory=list)
    created_at: str = ""
    tags: List[str] = field(default_factory=list)


class ComplianceService:
    """Service for compliance intelligence and lessons learned."""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.compliance_dir = self.storage_dir / "compliance"
        self.compliance_dir.mkdir(parents=True, exist_ok=True)
        self._checks = self._load_checks()
        self._lessons = self._load_lessons()

    def _load_checks(self) -> List[ComplianceCheck]:
        check_file = self.compliance_dir / "checks.json"
        if check_file.exists():
            data = json.loads(check_file.read_text(encoding="utf-8"))
            return [ComplianceCheck(**c) for c in data]
        return []

    def _save_checks(self):
        check_file = self.compliance_dir / "checks.json"
        data = [vars(c) for c in self._checks]
        check_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_lessons(self) -> List[LessonLearned]:
        lesson_file = self.compliance_dir / "lessons.json"
        if lesson_file.exists():
            data = json.loads(lesson_file.read_text(encoding="utf-8"))
            return [LessonLearned(**l) for l in data]
        return []

    def _save_lessons(self):
        lesson_file = self.compliance_dir / "lessons.json"
        data = [vars(l) for l in self._lessons]
        lesson_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_compliance_check(self, standard: str, section: str, requirement: str) -> ComplianceCheck:
        check_id = f"CHK-{len(self._checks) + 1:04d}"
        check = ComplianceCheck(
            id=check_id,
            standard=standard,
            section=section,
            requirement=requirement,
            status="pending",
            last_checked=datetime.now().isoformat(),
        )
        self._checks.append(check)
        self._save_checks()
        return check

    def update_check_status(self, check_id: str, status: str, evidence: List[str] = None) -> Optional[ComplianceCheck]:
        for check in self._checks:
            if check.id == check_id:
                check.status = status
                check.last_checked = datetime.now().isoformat()
                if evidence:
                    check.evidence = evidence
                self._save_checks()
                return check
        return None

    def add_lesson(self, title: str, description: str, category: str, equipment_tags: List[str] = None, tags: List[str] = None) -> LessonLearned:
        lesson_id = f"LL-{len(self._lessons) + 1:04d}"
        lesson = LessonLearned(
            id=lesson_id,
            title=title,
            description=description,
            category=category,
            equipment_tags=equipment_tags or [],
            created_at=datetime.now().isoformat(),
            tags=tags or [],
        )
        self._lessons.append(lesson)
        self._save_lessons()
        return lesson

    def get_compliance_status(self, standard: Optional[str] = None) -> Dict[str, Any]:
        checks = self._checks
        if standard:
            checks = [c for c in checks if c.standard == standard]

        total = len(checks)
        compliant = len([c for c in checks if c.status == "compliant"])
        non_compliant = len([c for c in checks if c.status == "non_compliant"])
        pending = len([c for c in checks if c.status == "pending"])

        return {
            "total": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "pending": pending,
            "compliance_rate": (compliant / total * 100) if total > 0 else 0,
        }

    def get_lessons_learned(self, category: Optional[str] = None, equipment_tag: Optional[str] = None) -> List[Dict]:
        lessons = self._lessons
        if category:
            lessons = [l for l in lessons if l.category == category]
        if equipment_tag:
            lessons = [l for l in lessons if equipment_tag in l.equipment_tags]
        return [vars(l) for l in lessons]

    def search_lessons(self, query: str) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for lesson in self._lessons:
            searchable = f"{lesson.title} {lesson.description} {' '.join(lesson.tags)}".lower()
            if query_lower in searchable:
                results.append(vars(lesson))
        return results

    def get_compliance_checks(self, standard: Optional[str] = None) -> List[Dict]:
        checks = self._checks
        if standard:
            checks = [c for c in checks if c.standard == standard]
        return [vars(c) for c in checks]
