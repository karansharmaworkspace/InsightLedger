"""
Maintenance Intelligence Service
Predictive maintenance and root cause analysis.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class WorkOrder:
    id: str
    equipment_tag: str
    description: str
    priority: str  # low, medium, high, critical
    status: str  # open, in_progress, completed
    created_at: str
    completed_at: Optional[str] = None
    root_cause: Optional[str] = None
    actions_taken: List[str] = field(default_factory=list)


@dataclass
class EquipmentHealth:
    equipment_tag: str
    health_score: float  # 0-100
    last_maintenance: Optional[str] = None
    next_maintenance: Optional[str] = None
    failure_probability: float = 0.0
    recommended_actions: List[str] = field(default_factory=list)


class MaintenanceService:
    """Service for maintenance intelligence and RCA."""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.maintenance_dir = self.storage_dir / "maintenance"
        self.maintenance_dir.mkdir(parents=True, exist_ok=True)
        self._work_orders = self._load_work_orders()

    def _load_work_orders(self) -> List[WorkOrder]:
        """Load work orders from storage."""
        wo_file = self.maintenance_dir / "work_orders.json"
        if wo_file.exists():
            data = json.loads(wo_file.read_text(encoding="utf-8"))
            return [WorkOrder(**wo) for wo in data]
        return []

    def _save_work_orders(self):
        """Save work orders to storage."""
        wo_file = self.maintenance_dir / "work_orders.json"
        data = [vars(wo) for wo in self._work_orders]
        wo_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create_work_order(self, equipment_tag: str, description: str, priority: str = "medium") -> WorkOrder:
        """Create a new work order."""
        wo_id = f"WO-{len(self._work_orders) + 1:04d}"
        wo = WorkOrder(
            id=wo_id,
            equipment_tag=equipment_tag,
            description=description,
            priority=priority,
            status="open",
            created_at=datetime.now().isoformat(),
        )
        self._work_orders.append(wo)
        self._save_work_orders()
        return wo

    def complete_work_order(self, wo_id: str, root_cause: str, actions: List[str]) -> Optional[WorkOrder]:
        """Complete a work order with root cause analysis."""
        for wo in self._work_orders:
            if wo.id == wo_id:
                wo.status = "completed"
                wo.completed_at = datetime.now().isoformat()
                wo.root_cause = root_cause
                wo.actions_taken = actions
                self._save_work_orders()
                return wo
        return None

    def get_equipment_health(self, equipment_tag: str) -> EquipmentHealth:
        """Calculate equipment health based on work orders."""
        equipment_orders = [wo for wo in self._work_orders if wo.equipment_tag == equipment_tag]

        if not equipment_orders:
            return EquipmentHealth(
                equipment_tag=equipment_tag,
                health_score=100.0,
                recommended_actions=["No maintenance history available"],
            )

        completed = [wo for wo in equipment_orders if wo.status == "completed"]
        recent_failures = [
            wo for wo in completed
            if wo.completed_at and datetime.fromisostring(wo.completed_at) > datetime.now() - timedelta(days=90)
        ]

        health_score = max(0, 100 - (len(recent_failures) * 15) - (len([wo for wo in equipment_orders if wo.status == "open"]) * 10))

        failure_prob = min(1.0, len(recent_failures) * 0.1)

        actions = []
        if health_score < 50:
            actions.append("Schedule immediate inspection")
        if failure_prob > 0.3:
            actions.append("Order spare parts")
        if len(recent_failures) > 2:
            actions.append("Review maintenance procedure")

        return EquipmentHealth(
            equipment_tag=equipment_tag,
            health_score=health_score,
            failure_probability=failure_prob,
            recommended_actions=actions or ["Continue normal operation"],
        )

    def analyze_root_cause(self, problem_description: str, equipment_tag: str) -> Dict[str, Any]:
        """Perform 5-Why root cause analysis."""
        equipment_orders = [wo for wo in self._work_orders if wo.equipment_tag == equipment_tag]
        recent_causes = [wo.root_cause for wo in equipment_orders if wo.root_cause]

        analysis = {
            "problem": problem_description,
            "equipment": equipment_tag,
            "historical_causes": recent_causes[:5],
            "five_whys": [
                {"why": "Why did the problem occur?", "answer": "Under investigation"},
                {"why": "Why was that condition present?", "answer": "Under investigation"},
                {"why": "Why wasn't it detected earlier?", "answer": "Under investigation"},
                {"why": "Why did the system allow this?", "answer": "Under investigation"},
                {"why": "Why wasn't this prevented?", "answer": "Under investigation"},
            ],
            "recommendations": [
                "Review maintenance logs",
                "Check equipment condition",
                "Analyze operating parameters",
            ],
        }

        if recent_causes:
            analysis["five_whys"][0]["answer"] = f"Similar to previous: {recent_causes[0]}"

        return analysis

    def get_work_orders(self, status: Optional[str] = None, equipment_tag: Optional[str] = None) -> List[Dict]:
        """Get work orders with optional filters."""
        orders = self._work_orders

        if status:
            orders = [wo for wo in orders if wo.status == status]
        if equipment_tag:
            orders = [wo for wo in orders if wo.equipment_tag == equipment_tag]

        return [vars(wo) for wo in orders]

    def get_maintenance_stats(self) -> Dict[str, Any]:
        """Get maintenance statistics."""
        total = len(self._work_orders)
        open_orders = len([wo for wo in self._work_orders if wo.status == "open"])
        completed = len([wo for wo in self._work_orders if wo.status == "completed"])

        return {
            "total_work_orders": total,
            "open": open_orders,
            "completed": completed,
            "in_progress": total - open_orders - completed,
        }
