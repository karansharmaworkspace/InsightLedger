"""
Entity Extraction Service
Extracts equipment tags, process parameters, and regulatory references from text.
"""
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Equipment:
    id: str
    tag: str
    name: str
    equipment_type: str
    location: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    documents: List[str] = field(default_factory=list)


@dataclass
class ProcessParameter:
    name: str
    value: float
    unit: str
    equipment_tag: Optional[str] = None


@dataclass
class RegulatoryRef:
    standard: str
    section: str
    description: str


@dataclass
class ExtractedEntities:
    equipment: List[Equipment]
    parameters: List[ProcessParameter]
    regulations: List[RegulatoryRef]
    personnel: List[str]
    dates: List[str]


EQUIPMENT_PATTERNS = {
    "pump": re.compile(r'(?:PUMP|Pmp)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "valve": re.compile(r'(?:VLV|Valve|VLV)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "vessel": re.compile(r'(?:VSL|Vessel|VES)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "heat_exchanger": re.compile(r'(?:HX|HE|Heat\s*Exchanger)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "compressor": re.compile(r'(?:CMP|Compressor|Cmpr)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "tank": re.compile(r'(?:TK|Tank|TANK)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "filter": re.compile(r'(?:FLT|Filter|FILT)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "mixer": re.compile(r'(?:MIX|Mixer|MIXR)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "column": re.compile(r'(?:COL|Column|COLM)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "furnace": re.compile(r'(?:FRN|Furnace|FURN)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "boiler": re.compile(r'(?:BLR|Boiler|BLR)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "motor": re.compile(r'(?:MOT|Motor|MOTR)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "sensor": re.compile(r'(?:SENS|Sensor|SNSR)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "transmitter": re.compile(r'(?:TXT|Transmitter|XMIT)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
    "switch": re.compile(r'(?:SW|Switch|SWTC)-?([A-Z]*\d+[A-Z]*)', re.IGNORECASE),
}

GENERAL_TAG = re.compile(
    r'\b([A-Z]{2,5}[-]?[A-Z]*\d{2,5}[A-Z]*)\b'
)

PARAMETER_PATTERNS = {
    "temperature": re.compile(r'(\d+(?:\.\d+)?)\s*(?:°C|°F|C|F|deg\s*C|deg\s*F|celsius|fahrenheit)', re.IGNORECASE),
    "pressure": re.compile(r'(\d+(?:\.\d+)?)\s*(?:bar|psi|kPa|MPa|kg/cm²|kg/cm2|psig|barg)', re.IGNORECASE),
    "flow_rate": re.compile(r'(\d+(?:\.\d+)?)\s*(?:m³/h|m3/h|LPM|GPM|l/min|m3/hr|NM3/H|Sm³/h)', re.IGNORECASE),
    "level": re.compile(r'(\d+(?:\.\d+)?)\s*(?:%|percent|mm|m|cm|inch|in)', re.IGNORECASE),
    "speed": re.compile(r'(\d+(?:\.\d+)?)\s*(?:rpm|RPM|Hz|赫兹)', re.IGNORECASE),
    "vibration": re.compile(r'(\d+(?:\.\d+)?)\s*(?:mm/s|micron|mils)', re.IGNORECASE),
}

REGULATORY_PATTERNS = {
    "Factory Act": re.compile(r'Factory\s*Act(?:\s*(?:of\s*)?\d{4})?(?:\s*,?\s*Section\s*(\d+[A-Z]?))?', re.IGNORECASE),
    "OISD": re.compile(r'OISD[-\s]*(\d{3}(?:[-]\d+[A-Z]*)?)', re.IGNORECASE),
    "PESO": re.compile(r'PESO(?:\s*(?:Regulation|Rule|Circular)\s*(\d+[A-Z]*))?', re.IGNORECASE),
    "IS": re.compile(r'\bIS\s*[:\s]*(\d{4,5}(?:[-]\d+[A-Z]*)?)', re.IGNORECASE),
    "API": re.compile(r'\bAPI\s*[:\s]*(\d{3}[A-Z]?(?:[-]\d+[A-Z]*)?)', re.IGNORECASE),
    "ASME": re.compile(r'\bASME\s*[:\s]*(\w+(?:[-]\d+[A-Z]*)?)', re.IGNORECASE),
    "NFPA": re.compile(r'\bNFPA\s*[:\s]*(\d{1,3}[A-Z]?(?:[-]\d+[A-Z]*)?)', re.IGNORECASE),
}

DATE_PATTERNS = [
    re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b'),
    re.compile(r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b', re.IGNORECASE),
    re.compile(r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b', re.IGNORECASE),
]

PERSONNEL_PATTERN = re.compile(
    r'(?:Mr\.|Mrs\.|Ms\.|Dr\.|Shri\.|Smt\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
)


class EntityExtractionService:
    """Service for extracting entities from industrial documents."""

    def __init__(self):
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
            except (ImportError, OSError):
                self._nlp = None
        return self._nlp

    def extract_equipment(self, text: str) -> List[Equipment]:
        """Extract equipment tags from text."""
        found = {}
        for eq_type, pattern in EQUIPMENT_PATTERNS.items():
            for match in pattern.finditer(text):
                tag_id = match.group(1)
                tag = f"{eq_type.upper()[:3]}-{tag_id}"
                if tag not in found:
                    found[tag] = Equipment(
                        id=tag.lower(),
                        tag=tag,
                        name=f"{eq_type.replace('_', ' ').title()} {tag_id}",
                        equipment_type=eq_type,
                    )

        for match in GENERAL_TAG.finditer(text):
            tag = match.group(1)
            if tag not in found and len(tag) >= 4:
                eq_type = "unknown"
                for etype, pattern in EQUIPMENT_PATTERNS.items():
                    if pattern.match(tag):
                        eq_type = etype
                        break
                found[tag] = Equipment(
                    id=tag.lower(),
                    tag=tag,
                    name=tag,
                    equipment_type=eq_type,
                )

        return list(found.values())

    def extract_parameters(self, text: str) -> List[ProcessParameter]:
        """Extract process parameters from text."""
        params = []
        for param_name, pattern in PARAMETER_PATTERNS.items():
            for match in pattern.finditer(text):
                value = float(match.group(1))
                unit = match.group(0).replace(str(value), "").strip()
                params.append(ProcessParameter(
                    name=param_name,
                    value=value,
                    unit=unit,
                ))
        return params

    def extract_regulations(self, text: str) -> List[RegulatoryRef]:
        """Extract regulatory references from text."""
        refs = []
        for standard, pattern in REGULATORY_PATTERNS.items():
            for match in pattern.finditer(text):
                section = match.group(1) if match.lastindex else ""
                refs.append(RegulatoryRef(
                    standard=standard,
                    section=section or "General",
                    description=match.group(0),
                ))
        return refs

    def extract_dates(self, text: str) -> List[str]:
        """Extract dates from text."""
        dates = []
        for pattern in DATE_PATTERNS:
            for match in pattern.finditer(text):
                dates.append(match.group(1))
        return list(set(dates))

    def extract_personnel(self, text: str) -> List[str]:
        """Extract personnel names from text."""
        if self.nlp:
            doc = self.nlp(text)
            names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            return list(set(names))

        found = set()
        for match in PERSONNEL_PATTERN.finditer(text):
            name = match.group(1).strip()
            if len(name.split()) >= 2:
                found.add(name)
        return list(found)

    def extract_all(self, text: str, document_id: str = "") -> ExtractedEntities:
        """Extract all entity types from text."""
        return ExtractedEntities(
            equipment=self.extract_equipment(text),
            parameters=self.extract_parameters(text),
            regulations=self.extract_regulations(text),
            personnel=self.extract_personnel(text),
            dates=self.extract_dates(text),
        )
