"""Maintenance Intelligence module.

Analyzes work orders, failure records, and equipment history to provide
predictive maintenance recommendations and RCA support.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any


# Failure mode categories (ISO 14224)
FAILURE_CATEGORIES = {
    "mechanical": ["leak", "vibration", "wear", "corrosion", "crack", "seizure", "alignment"],
    "electrical": ["short circuit", "open circuit", "insulation", "grounding", "overload"],
    "instrumentation": ["calibration", "drift", "failure", "stuck", "erratic", "bias"],
    "process": ["overflow", "underflow", "high temperature", "low pressure", "fouling"],
}

# Severity levels
SEVERITY_MAP = {
    "critical": ["safety", "environmental", "shutdown", "emergency", "critical", "fire", "explosion"],
    "high": ["production loss", "degradation", "performance", "efficiency"],
    "medium": ["inspection", "preventive", "scheduled", "minor"],
    "low": ["housekeeping", "cosmetic", "documentation"],
}


class MaintenanceRecord:
    """A maintenance work order or failure record."""

    def __init__(
        self,
        equipment_tag: str,
        record_type: str,
        description: str,
        date: str | None = None,
        priority: str = "medium",
        status: str = "open",
        root_cause: str | None = None,
        action_taken: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.equipment_tag = equipment_tag
        self.record_type = record_type
        self.description = description
        self.date = date
        self.priority = priority
        self.status = status
        self.root_cause = root_cause
        self.action_taken = action_taken
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "equipment_tag": self.equipment_tag,
            "record_type": self.record_type,
            "description": self.description,
            "date": self.date,
            "priority": self.priority,
            "status": self.status,
            "root_cause": self.root_cause,
            "action_taken": self.action_taken,
            "metadata": self.metadata,
        }


class MaintenanceIntelligence:
    """Analyze maintenance records for patterns and recommendations."""

    def __init__(self):
        self.records: list[MaintenanceRecord] = []

    def add_record(self, record: MaintenanceRecord):
        self.records.append(record)

    def add_records_from_text(self, text: str, source: str = "unknown"):
        """Parse maintenance records from unstructured text."""
        # Simple heuristic extraction
        lines = text.split("\n")
        current_record = {}

        for line in lines:
            line = line.strip()
            if not line:
                if current_record.get("equipment_tag"):
                    self.records.append(MaintenanceRecord(
                        equipment_tag=current_record["equipment_tag"],
                        record_type=current_record.get("record_type", "work_order"),
                        description=current_record.get("description", ""),
                        date=current_record.get("date"),
                        priority=current_record.get("priority", "medium"),
                        root_cause=current_record.get("root_cause"),
                        action_taken=current_record.get("action_taken"),
                        metadata={"source": source},
                    ))
                current_record = {}
                continue

            # Extract equipment tag
            tag_match = re.search(r'\b([A-Z]{1,4}-\d{3,4}[A-Z]?)\b', line)
            if tag_match:
                current_record["equipment_tag"] = tag_match.group(1)

            # Extract date
            date_match = re.search(r'\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\b', line)
            if date_match:
                current_record["date"] = date_match.group(1)

            # Classify record type
            line_lower = line.lower()
            if any(w in line_lower for w in ["work order", "wo#", "wo-", "maintenance"]):
                current_record["record_type"] = "work_order"
            elif any(w in line_lower for w in ["failure", "breakdown", "fault", "defect"]):
                current_record["record_type"] = "failure"
            elif any(w in line_lower for w in ["inspection", "check", "survey"]):
                current_record["record_type"] = "inspection"

            # Severity
            for sev, keywords in SEVERITY_MAP.items():
                if any(kw in line_lower for kw in keywords):
                    current_record["priority"] = sev
                    break

            # Root cause
            if any(w in line_lower for w in ["root cause", "cause:", "reason:"]):
                current_record["root_cause"] = line

            # Action
            if any(w in line_lower for w in ["action taken", "corrective", "repaired", "replaced"]):
                current_record["action_taken"] = line

            # Description accumulation
            if "description" not in current_record:
                current_record["description"] = line
            else:
                current_record["description"] += " " + line

        # Flush last record if non-empty
        if current_record.get("equipment_tag"):
            self.records.append(MaintenanceRecord(
                equipment_tag=current_record["equipment_tag"],
                record_type=current_record.get("record_type", "work_order"),
                description=current_record.get("description", ""),
                date=current_record.get("date"),
                priority=current_record.get("priority", "medium"),
                root_cause=current_record.get("root_cause"),
                action_taken=current_record.get("action_taken"),
                metadata={"source": source},
            ))

    def get_equipment_history(self, equipment_tag: str) -> list[dict[str, Any]]:
        """Get all records for a specific equipment tag."""
        return [r.to_dict() for r in self.records if r.equipment_tag == equipment_tag]

    def get_failure_patterns(self) -> dict[str, Any]:
        """Analyze failure patterns across all records."""
        failure_records = [r for r in self.records if r.record_type == "failure"]

        # Failure frequency by equipment
        equip_failures = Counter(r.equipment_tag for r in failure_records)

        # Failure categories
        category_counts = Counter()
        for record in failure_records:
            desc_lower = record.description.lower()
            for cat, keywords in FAILURE_CATEGORIES.items():
                if any(kw in desc_lower for kw in keywords):
                    category_counts[cat] += 1

        # MTBF calculation (simplified)
        mtbf_data = {}
        for tag in equip_failures:
            tag_records = sorted(
                [r for r in failure_records if r.equipment_tag == tag and r.date],
                key=lambda x: x.date or "0000-00-00",
            )
            if len(tag_records) >= 2:
                dates = [datetime.strptime(r.date, "%Y-%m-%d") for r in tag_records if r.date]
                if len(dates) >= 2:
                    deltas = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
                    mtbf_data[tag] = sum(deltas) / len(deltas)

        return {
            "total_failures": len(failure_records),
            "top_equipments": dict(equip_failures.most_common(10)),
            "failure_categories": dict(category_counts),
            "mtbf_days": mtbf_data,
        }

    def get_maintenance_recommendations(self, equipment_tag: str) -> list[str]:
        """Generate maintenance recommendations based on history."""
        history = self.get_equipment_history(equipment_tag)
        if not history:
            return ["No maintenance history found for this equipment."]

        recommendations = []
        failures = [r for r in history if r["record_type"] == "failure"]
        inspections = [r for r in history if r["record_type"] == "inspection"]

        # High failure frequency
        if len(failures) >= 3:
            recommendations.append(
                f"⚠️ High failure frequency ({len(failures)} failures). "
                "Consider root cause analysis and redesign."
            )

        # Check for recurring failure modes
        failure_descs = " ".join(r["description"].lower() for r in failures)
        for cat, keywords in FAILURE_CATEGORIES.items():
            count = sum(1 for kw in keywords if kw in failure_descs)
            if count >= 2:
                recommendations.append(
                    f"🔄 Recurring {cat} issues detected. "
                    f"Investigate systemic {cat} problems."
                )

        # No recent inspections
        if not inspections:
            recommendations.append("📋 No inspection records found. Schedule preventive inspection.")

        # Priority based on severity
        critical = [r for r in history if r.get("priority") == "critical"]
        if critical:
            recommendations.append(
                f"🚨 {len(critical)} critical incidents recorded. "
                "Review safety protocols immediately."
            )

        if not recommendations:
            recommendations.append("✅ Equipment history looks normal. Continue routine maintenance.")

        return recommendations

    def get_rca_suggestions(self, equipment_tag: str, failure_description: str) -> list[str]:
        """Suggest root cause analysis approaches."""
        suggestions = [
            "5-Why Analysis: Ask 'why' repeatedly to drill down to root cause.",
            "Fishbone Diagram: Categorize potential causes (Man, Machine, Material, Method, Environment).",
            "Fault Tree Analysis: Work backwards from failure to identify contributing factors.",
        ]

        desc_lower = failure_description.lower()

        # Add specific suggestions based on failure type
        for cat, keywords in FAILURE_CATEGORIES.items():
            if any(kw in desc_lower for kw in keywords):
                suggestions.append(f"Focus on {cat} factors: check related {cat} records for this equipment.")

        # Check history for patterns
        history = self.get_equipment_history(equipment_tag)
        if history:
            cutoff = datetime.now().strftime("%Y-%m-%d")
            recent = [r for r in history if (r.get("date") or "") >= cutoff[:4] + "-01-01"]
            if recent:
                suggestions.append(f"Review {len(recent)} recent records for this equipment to identify trends.")

        return suggestions
