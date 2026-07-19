# Plan: Phase 4 — Entity Extraction & OKF Knowledge Graph

## Goal
Extract entities from documents and build unified knowledge graph using OKF bundles.

## Requirement IDs
ING-05, ING-06, KG-01, KG-02, KG-03, KG-04

## Success Criteria
1. Equipment tag recognition using regex + NER working
2. Process parameter extraction (temperature, pressure, flow) functional
3. Regulatory reference detection (Factory Act, OISD, PESO) working
4. OKF concept creation for equipment, procedures, incidents
5. Cross-linking between concepts implemented
6. Knowledge graph query API operational
7. Incremental graph updates working

## Tasks

### Task 4.1: Equipment Tag Recognition
- [ ] Define regex patterns for equipment tags (PUMP-A101, VLV-B202)
- [ ] Implement NER for equipment names
- [ ] Extract equipment from text and tables
- [ ] Store equipment entities in OKF

### Task 4.2: Process Parameter Extraction
- [ ] Extract temperature values (with units)
- [ ] Extract pressure values (with units)
- [ ] Extract flow rates and levels
- [ ] Link parameters to equipment

### Task 4.3: Regulatory Reference Detection
- [ ] Detect Factory Act section references
- [ ] Detect OISD standard references
- [ ] Detect PESO regulation references
- [ ] Extract compliance requirements

### Task 4.4: Personnel & Date Extraction
- [ ] Extract personnel names using NER
- [ ] Extract dates and timestamps
- [ ] Link personnel to activities
- [ ] Track document authorship

### Task 4.5: OKF Bundle Creation
- [ ] Create OKF concepts for equipment
- [ ] Create OKF concepts for procedures
- [ ] Create OKF concepts for incidents
- [ ] Create OKF concepts for standards

### Task 4.6: Cross-Linking
- [ ] Link equipment to documents
- [ ] Link equipment to procedures
- [ ] Link incidents to equipment
- [ ] Link standards to equipment

### Task 4.7: Knowledge Graph API
- [ ] Create `GET /api/knowledge-graph` endpoint
- [ ] Support structured queries (type, tags, links)
- [ ] Implement graph traversal queries
- [ ] Add search across knowledge graph

### Task 4.8: Incremental Updates
- [ ] Detect new documents for processing
- [ ] Extract entities from new documents
- [ ] Update knowledge graph incrementally
- [ ] Maintain graph consistency

## Technical Design

### API Endpoints
- `GET /api/knowledge-graph` - Query knowledge graph
- `GET /api/equipment` - List all equipment
- `GET /api/equipment/{id}` - Get equipment details
- `GET /api/search` - Search across knowledge graph

### Data Models
```python
class Equipment:
    id: str
    tag: str  # PUMP-A101
    name: str
    type: str
    location: str
    parameters: Dict[str, Any]
    documents: List[str]
    procedures: List[str]

class Procedure:
    id: str
    name: str
    equipment: List[str]
    steps: List[str]
    references: List[str]

class Incident:
    id: str
    date: datetime
    equipment: List[str]
    description: str
    root_cause: str
    actions: List[str]
```

### OKF Bundle Structure
```
data/industrial-kb/
├── log.md
├── equipment/
│   ├── pump-a101.md
│   └── vlv-b202.md
├── procedures/
│   ├── maintenance-pump.md
│   └── startup-sequence.md
├── incidents/
│   ├── incident-001.md
│   └── incident-002.md
└── standards/
    ├── factory-act.md
    └── oisd-116.md
```

### Dependencies
```txt
spacy==3.7.2
networkx==3.2.1
```

## Verification

### Unit Tests
- Test equipment tag extraction
- Test process parameter extraction
- Test regulatory reference detection
- Test OKF bundle creation

### Integration Tests
- Test knowledge graph building
- Test cross-linking
- Test query API

### Manual Verification
- Ingest sample documents
- Verify equipment extraction
- Check knowledge graph structure

## Dependencies
- Phase 1: Project Setup & Core Infrastructure
- Phase 2: PDF & Document Ingestion Pipeline
- Phase 3: OCR & Scanned Document Processing

## Timeline
- Task 4.1: 2 hours
- Task 4.2: 1.5 hours
- Task 4.3: 1.5 hours
- Task 4.4: 1 hour
- Task 4.5: 1.5 hours
- Task 4.6: 1.5 hours
- Task 4.7: 1.5 hours
- Task 4.8: 1 hour
- **Total: 11.5 hours**

## Risks
1. **Entity disambiguation**: Same equipment may have different names
   - Mitigation: Fuzzy matching, manual review
2. **Regex complexity**: Industrial naming conventions vary
   - Mitigation: Extensible pattern system
