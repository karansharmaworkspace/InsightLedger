"""Entity extraction from industrial documents.

Extracts: equipment tags, process parameters, dates, personnel, regulatory refs.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any


# Industrial equipment tag patterns (ISA-5.1, ISO 14224)
TAG_PATTERNS = [
    # Equipment tags: V-101, P-202A, HX-301
    re.compile(r'\b([A-Z]{1,4}-\d{3,4}[A-Z]?)\b'),
    # Instrument tags: TI-101, PI-202, FIC-301, LIC-401
    re.compile(r'\b(TI|PI|FI|FIC|PIC|LIC|TIC|AIC|SI|DI|XI|PCV|FCV|LCV|TCV|SDV|BDV|PSV|PRV|CV)-(\d{3,4})\b'),
    # Loop tags: 101-IC-001
    re.compile(r'\b(\d{3}-IC-\d{3})\b'),
]

# Process parameter patterns
PARAM_PATTERNS = [
    # Temperature: 150°C, 300 F, 450K
    re.compile(r'\b(\d+(?:\.\d+)?)\s*°?\s*([CFK])\b', re.IGNORECASE),
    # Pressure: 150 psi, 10 bar, 5 MPa, 150 psig
    re.compile(r'\b(\d+(?:\.\d+)?)\s*(psi[sg]?|bar|kpa|mpa|atm|mmhg|torr)\b', re.IGNORECASE),
    # Flow: 500 gpm, 100 m3/h, 50 L/min
    re.compile(r'\b(\d+(?:\.\d+)?)\s*(gpm|lpm|m3\/h|l\/min|kg\/s|t\/h)\b', re.IGNORECASE),
    # Level: 75%, 2.5 m, 10 ft
    re.compile(r'\b(\d+(?:\.\d+)?)\s*(%|m|ft|in|mm|cm)\b'),
]

# Date patterns
DATE_PATTERNS = [
    # ISO: 2024-01-15, 2024/01/15
    re.compile(r'\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b'),
    # US: 01/15/2024, 1/15/2024
    re.compile(r'\b(0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])[-/](20\d{2})\b'),
    # Indian: 15-01-2024, 15/01/2024
    re.compile(r'\b(0[1-9]|[12]\d|3[01])[-/](0[1-9]|1[0-2])[-/](20\d{2})\b'),
]

# Personnel patterns
PERSONNEL_PATTERNS = [
    # Names: "by John Smith", "approved by J. Doe"
    re.compile(r'\b(?:by|approved by|reviewed by|checked by|signed by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', re.IGNORECASE),
    # Employee IDs: EMP-001, ID-12345
    re.compile(r'\b(?:EMP|ID|EN)-(\d{3,6})\b'),
]

# Regulatory patterns
REGULATORY_PATTERNS = [
    # Standards: ISO 9001, API 570, ASME B31.3
    re.compile(r'\b(ISO|API|ASME|ASTM|ISA|IEC|ANSI|NFPA|OISD|PESO|BIS)-?\s*(\d{2,5}(?:\.\d+)?)\b', re.IGNORECASE),
    # Factory Act (no number)
    re.compile(r'\b(FACTORY\s+ACT)\b', re.IGNORECASE),
    # OISD norms
    re.compile(r'\bOISD-?(\d{2,4})\b', re.IGNORECASE),
    # PESO approvals
    re.compile(r'\bPESO\s*(?:approval|cert|license)\s*(?:no\.?)?\s*([A-Z0-9-]+)', re.IGNORECASE),
]


class Entity:
    """An extracted entity."""

    def __init__(self, entity_type: str, value: str, context: str, confidence: float = 0.8):
        self.entity_type = entity_type
        self.value = value
        self.context = context
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.entity_type,
            "value": self.value,
            "context": self.context,
            "confidence": self.confidence,
        }


class EntityExtractor:
    """Extract industrial entities from text."""

    def extract(self, text: str) -> list[Entity]:
        entities = []
        entities.extend(self._extract_tags(text))
        entities.extend(self._extract_parameters(text))
        entities.extend(self._extract_dates(text))
        entities.extend(self._extract_personnel(text))
        entities.extend(self._extract_regulatory(text))
        return entities

    def _extract_tags(self, text: str) -> list[Entity]:
        entities = []
        seen = set()
        for pattern in TAG_PATTERNS:
            for match in pattern.finditer(text):
                tag = match.group(0)
                if tag not in seen:
                    seen.add(tag)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].strip()
                    entities.append(Entity("equipment_tag", tag, context))
        return entities

    def _extract_parameters(self, text: str) -> list[Entity]:
        entities = []
        seen = set()
        for pattern in PARAM_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(0)
                if value not in seen:
                    seen.add(value)
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    context = text[start:end].strip()
                    entities.append(Entity("process_parameter", value, context))
        return entities

    def _extract_dates(self, text: str) -> list[Entity]:
        entities = []
        seen = set()
        for pattern in DATE_PATTERNS:
            for match in pattern.finditer(text):
                date_str = match.group(0)
                if date_str not in seen:
                    seen.add(date_str)
                    entities.append(Entity("date", date_str, date_str))
        return entities

    def _extract_personnel(self, text: str) -> list[Entity]:
        entities = []
        seen = set()
        for pattern in PERSONNEL_PATTERNS:
            for match in pattern.finditer(text):
                name = match.group(1) if match.lastindex else match.group(0)
                if name and name not in seen:
                    seen.add(name)
                    entities.append(Entity("personnel", name.strip(), match.group(0)))
        return entities

    def _extract_regulatory(self, text: str) -> list[Entity]:
        entities = []
        seen = set()
        for pattern in REGULATORY_PATTERNS:
            for match in pattern.finditer(text):
                ref = match.group(0)
                if ref not in seen:
                    seen.add(ref)
                    entities.append(Entity("regulatory_ref", ref.strip(), ref))
        return entities

    def extract_structured(self, text: str) -> dict[str, list[str]]:
        entities = self.extract(text)
        result: dict[str, list[str]] = {}
        for e in entities:
            if e.entity_type not in result:
                result[e.entity_type] = []
            if e.value not in result[e.entity_type]:
                result[e.entity_type].append(e.value)
        return result
