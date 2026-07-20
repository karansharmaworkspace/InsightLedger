"""Compliance & Regulatory Intelligence module.

Maps regulatory requirements against procedures and equipment states,
identifies compliance gaps, and generates audit evidence packages.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any


# Indian industrial regulations
REGULATIONS = {
    "factory_act": {
        "name": "Factories Act, 1948",
        "areas": ["safety", "health", "welfare", "working conditions"],
        "keywords": ["factory", "worker", "safety", "health", "inspection", "license"],
    },
    "oisd": {
        "name": "OISD Standards",
        "areas": ["oil industry", "safety", "design", "construction"],
        "keywords": ["oisd", "oil industry", "safety directive"],
    },
    "peso": {
        "name": "PESO (Petroleum and Explosives Safety Organisation)",
        "areas": ["pressure vessels", "explosives", "gas cylinders", "LPG"],
        "keywords": ["peso", "pressure vessel", "explosive", "gas cylinder", "lpg", "approval"],
    },
    "iso_9001": {
        "name": "ISO 9001:2015 - Quality Management",
        "areas": ["quality", "management system", "continuous improvement"],
        "keywords": ["iso 9001", "quality management", "qms", "nonconformance"],
    },
    "iso_14001": {
        "name": "ISO 14001:2015 - Environmental Management",
        "areas": ["environment", "emissions", "waste", "pollution"],
        "keywords": ["iso 14001", "environmental", "emission", "waste", "pollution"],
    },
    "iso_45001": {
        "name": "ISO 45001:2018 - Occupational Health & Safety",
        "areas": ["occupational health", "safety", "risk assessment"],
        "keywords": ["iso 45001", "occupational", "health and safety", "ohsas"],
    },
    "api_570": {
        "name": "API 570 - Piping Inspection Code",
        "areas": ["piping", "inspection", "corrosion", "thickness"],
        "keywords": ["api 570", "piping inspection", "corrosion", "thickness"],
    },
    "api_510": {
        "name": "API 510 - Pressure Vessel Inspection",
        "areas": ["pressure vessels", "inspection", "repair", "alteration"],
        "keywords": ["api 510", "pressure vessel", "vessel inspection"],
    },
    "asme_b31_3": {
        "name": "ASME B31.3 - Process Piping",
        "areas": ["piping design", "materials", "fabrication", "testing"],
        "keywords": ["asme b31.3", "process piping", "piping design"],
    },
}


class ComplianceGap:
    """A compliance gap or deviation."""

    def __init__(
        self,
        regulation: str,
        requirement: str,
        current_state: str,
        gap_description: str,
        severity: str = "medium",
        recommendation: str = "",
    ):
        self.regulation = regulation
        self.requirement = requirement
        self.current_state = current_state
        self.gap_description = gap_description
        self.severity = severity
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, Any]:
        return {
            "regulation": self.regulation,
            "requirement": self.requirement,
            "current_state": self.current_state,
            "gap_description": self.gap_description,
            "severity": self.severity,
            "recommendation": self.recommendation,
        }


class ComplianceIntelligence:
    """Analyze documents for regulatory compliance."""

    def __init__(self):
        self.documents: list[dict[str, Any]] = []
        self.findings: list[dict[str, Any]] = []
        self.gaps: list[ComplianceGap] = []

    def add_document(self, doc: dict[str, Any]):
        self.documents.append(doc)

    def analyze_document(self, text: str, source: str = "unknown") -> dict[str, Any]:
        """Analyze a single document for compliance references and gaps."""
        text_lower = text.lower()
        analysis = {
            "source": source,
            "regulations_referenced": [],
            "compliance_status": "unknown",
            "gaps": [],
            "recommendations": [],
        }

        # Check for regulation references
        for reg_id, reg_info in REGULATIONS.items():
            for keyword in reg_info["keywords"]:
                if keyword in text_lower:
                    analysis["regulations_referenced"].append({
                        "id": reg_id,
                        "name": reg_info["name"],
                        "areas": reg_info["areas"],
                    })
                    break

        # Check for compliance indicators
        positive_indicators = [
            "compliant", "compliance", "approved", "certified", "verified",
            "inspected", "tested", "passed", "acceptable", "conforms",
        ]
        negative_indicators = [
            "non-compliant", "deviation", "nonconformance", "failure",
            "deficiency", "violation", "expired", "overdue", "pending",
        ]

        positive_count = sum(1 for ind in positive_indicators if ind in text_lower)
        negative_count = sum(1 for ind in negative_indicators if ind in text_lower)

        if negative_count > positive_count:
            analysis["compliance_status"] = "potential_issues"
        elif positive_count > 0:
            analysis["compliance_status"] = "compliant"
        else:
            analysis["compliance_status"] = "unverified"

        # Identify potential gaps
        gap_patterns = [
            (r"expired|overdue|not renewed", "Certification/inspection may be expired"),
            (r"pending|awaiting|not completed", "Action items pending completion"),
            (r"deviation|non.?conformance|failure", "Potential non-compliance detected"),
            (r"missing|absent|not found", "Required documentation may be missing"),
        ]

        for pattern, description in gap_patterns:
            if re.search(pattern, text_lower):
                analysis["gaps"].append(description)
                self.gaps.append(ComplianceGap(
                    regulation="general",
                    requirement=description,
                    current_state="flagged in document",
                    gap_description=description,
                    severity="medium",
                ))

        return analysis

    def analyze_corpus(self) -> dict[str, Any]:
        """Analyze entire document corpus for compliance."""
        all_analysis = []
        regulation_coverage = defaultdict(int)
        total_gaps = 0

        for doc in self.documents:
            text = doc.get("content", "")
            source = doc.get("source", "unknown")
            analysis = self.analyze_document(text, source)
            all_analysis.append(analysis)
            total_gaps += len(analysis["gaps"])

            for ref in analysis["regulations_referenced"]:
                regulation_coverage[ref["name"]] += 1

        return {
            "total_documents": len(self.documents),
            "regulation_coverage": dict(regulation_coverage),
            "total_gaps": total_gaps,
            "documents_with_gaps": sum(
                1 for a in all_analysis if a["gaps"]
            ),
            "compliance_status": (
                "issues_detected" if total_gaps > 0 else "no_issues_detected"
            ),
        }

    def get_audit_package(self) -> dict[str, Any]:
        """Generate compliance evidence package for audit."""
        corpus_analysis = self.analyze_corpus()

        # Group gaps by regulation
        gaps_by_regulation = defaultdict(list)
        for gap in self.gaps:
            gaps_by_regulation[gap.regulation].append(gap.to_dict())

        # Generate summary
        summary = {
            "audit_date": datetime.now().strftime("%Y-%m-%d"),
            "scope": "Full document corpus",
            "total_documents_reviewed": corpus_analysis["total_documents"],
            "regulations_in_scope": list(REGULATIONS.keys()),
            "regulation_coverage": corpus_analysis["regulation_coverage"],
            "findings_summary": {
                "total_gaps": corpus_analysis["total_gaps"],
                "gaps_by_regulation": dict(gaps_by_regulation),
            },
            "compliance_status": corpus_analysis["compliance_status"],
            "recommendations": self._generate_recommendations(),
        }

        return summary

    def _generate_recommendations(self) -> list[str]:
        recommendations = []

        if self.gaps:
            recommendations.append(
                f"Address {len(self.gaps)} identified compliance gaps before next audit."
            )

        # Check for missing regulation coverage
        covered = set()
        for doc in self.documents:
            text = doc.get("content", "").lower()
            for reg_id, reg_info in REGULATIONS.items():
                for keyword in reg_info["keywords"]:
                    if keyword in text:
                        covered.add(reg_id)
                        break

        missing = set(REGULATIONS.keys()) - covered
        if missing:
            missing_names = [REGULATIONS[r]["name"] for r in missing]
            recommendations.append(
                f"Review documentation for: {', '.join(missing_names)}"
            )

        if not recommendations:
            recommendations.append("No significant compliance issues detected.")

        return recommendations

    def check_equipment_compliance(self, equipment_tag: str, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """Check compliance status for a specific equipment."""
        relevant_docs = []
        for doc in documents:
            if equipment_tag in doc.get("content", ""):
                relevant_docs.append(doc)

        status = {
            "equipment_tag": equipment_tag,
            "related_documents": len(relevant_docs),
            "inspections_found": False,
            "certifications_found": False,
            "gaps": [],
        }

        for doc in relevant_docs:
            text = doc.get("content", "").lower()
            if "inspection" in text:
                status["inspections_found"] = True
            if any(w in text for w in ["certificate", "certified", "approval"]):
                status["certifications_found"] = True

        if not status["inspections_found"]:
            status["gaps"].append("No inspection records found")
        if not status["certifications_found"]:
            status["gaps"].append("No certification records found")

        return status
