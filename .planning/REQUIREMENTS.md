# Requirements: AI for Industrial Knowledge Intelligence

**Defined:** 2026-07-19
**Core Value:** Making fragmented industrial knowledge instantly accessible and actionable

## v1 Requirements

Requirements for hackathon prototype. Each maps to roadmap phases.

### Document Ingestion

- [ ] **ING-01**: System can ingest PDF documents (engineering drawings, manuals, reports)
- [ ] **ING-02**: System can ingest scanned documents with OCR processing
- [ ] **ING-03**: System can ingest spreadsheets (Excel, CSV) with structured data
- [ ] **ING-04**: System can ingest email archives with attachments
- [ ] **ING-05**: System can process P&ID diagrams and extract equipment tags
- [ ] **ING-06**: System can extract entities: equipment tags, process parameters, regulatory references, personnel, dates

### Knowledge Graph (OKF Format)

- [ ] **KG-01**: System builds unified knowledge graph using Open Knowledge Format (OKF) bundles
- [ ] **KG-02**: Knowledge graph updates automatically when new documents arrive (OKF log.md tracking)
- [ ] **KG-03**: System maintains document-to-entity relationships via OKF cross-links
- [ ] **KG-04**: System maintains entity-to-entity relationships via OKF markdown links
- [ ] **KG-05**: Knowledge graph is queryable via OKF structured queries (type, tags, links)

### Expert Knowledge Copilot

- [ ] **COP-01**: RAG-powered conversational AI answers operational queries across full document corpus
- [ ] **COP-02**: Responses include source citations with direct links to originating documents
- [ ] **COP-03**: Responses include confidence scores for answer quality
- [ ] **COP-04**: Interface works on mobile devices for field technicians
- [ ] **COP-05**: System handles maintenance and engineering domain questions
- [ ] **COP-06**: System provides time-to-answer improvement versus traditional search

### Maintenance Intelligence

- [ ] **MNT-01**: Agent fuses work order history with equipment failure records
- [ ] **MNT-02**: Agent incorporates OEM manuals and inspection findings
- [ ] **MNT-03**: Agent generates predictive maintenance recommendations
- [ ] **MNT-04**: Agent provides Root Cause Analysis (RCA) support
- [ ] **MNT-05**: Agent generates optimized maintenance schedules

### Compliance Intelligence

- [ ] **CMP-01**: System maps regulatory requirements (Factory Act, OISD, PESO) against current procedures
- [ ] **CMP-02**: System identifies compliance gaps between requirements and current state
- [ ] **CMP-03**: System can auto-generate compliance evidence packages for audits
- [ ] **CMP-04**: System flags quality deviations before they escalate

### Lessons Learned Engine

- [ ] **LL-01**: Agent analyses incident reports and near-miss records
- [ ] **LL-02**: Agent analyses audit findings and quality non-conformances
- [ ] **LL-03**: Agent identifies systemic patterns invisible to individual review
- [ ] **LL-04**: Agent proactively pushes warnings to operational teams before similar conditions recur

### User Experience

- [ ] **UX-01**: PyQt6 desktop GUI with crop, zoom, pan support
- [ ] **UX-02**: Search results appear within 5 seconds (time-to-answer improvement)
- [ ] **UX-03**: Interface provides intuitive navigation across document types
- [ ] **UX-04**: System provides visual knowledge graph exploration (vis.js or pyvis)
- [ ] **UX-05**: Dashboard shows compliance status and maintenance insights
- [ ] **UX-06**: AI Assistant powered by Groq Llama 3.3 for natural language queries
- [ ] **UX-07**: 605-class reclassification sidebar with thumbnails (like DPID AI)

### Tech Stack (DPID AI Compatible)

- [ ] **TS-01**: YOLOv8 (Ultralytics) for 32-class symbol detection
- [ ] **TS-02**: DINOv2 (Facebook Research) for 605-subclass reclassification
- [ ] **TS-03**: SAHI for tiled inference on large P&ID images (up to 7000px)
- [ ] **TS-04**: ensemble-boxes for Weighted Boxes Fusion (IoU=0.60)
- [ ] **TS-05**: OpenCV for image preprocessing (CLAHE, deskew)
- [ ] **TS-06**: TrOCR + DBNet for text recognition and detection
- [ ] **TS-07**: Groq API for fast LLM inference (Llama 3.3 70B)
- [ ] **TS-08**: ClassMemory system for user reclassification learning
- [ ] **TS-09**: VisualRAG for DINOv2-based reclassification gallery
- [ ] **TS-10**: Topology engine with HoughLinesP + BFS connectivity solver

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Real-time Integration

- **RT-01**: Real-time sensor data integration via IoT protocols
- **RT-02**: Live equipment monitoring and anomaly detection
- **RT-03**: Integration with SCADA systems

### Enterprise Features

- **ENT-01**: Multi-tenant architecture for enterprise deployment
- **ENT-02**: Role-based access control (RBAC)
- **ENT-03**: Audit trail for all user actions
- **ENT-04**: Integration with existing QMS systems

### Advanced AI

- **ADV-01**: Computer vision for automatic P&ID parsing
- **ADV-02**: Natural language processing for Indian language documents
- **ADV-03**: Predictive analytics for equipment failure
- **ADV-04**: Automated report generation

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time sensor data integration | Requires IoT infrastructure not available in hackathon |
| Full enterprise deployment | Hackathon prototype only, demo with sample data |
| Custom hardware/on-premise | Desktop-first with PyQt6, demo capability |
| Complete regulatory database | Use representative samples of Factory Act, OISD, PESO |
| Native mobile app | PyQt6 desktop GUI sufficient for demo |
| Multi-language support | Can add via deep-translator later |
| Full SCADA integration | Complex industrial protocol, out of scope |
| Web-based frontend | Using PyQt6 desktop GUI like DPID AI |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ING-01 | Phase 2 | Pending |
| ING-02 | Phase 3 | Pending |
| ING-03 | Phase 2 | Pending |
| ING-04 | Phase 2 | Pending |
| ING-05 | Phase 4 | Pending |
| ING-06 | Phase 4 | Pending |
| KG-01 | Phase 4 | Pending |
| KG-02 | Phase 4 | Pending |
| KG-03 | Phase 4 | Pending |
| KG-04 | Phase 4 | Pending |
| KG-05 | Phase 5 | Pending |
| COP-01 | Phase 6 | Pending |
| COP-02 | Phase 6 | Pending |
| COP-03 | Phase 6 | Pending |
| COP-04 | Phase 9 | Pending |
| COP-05 | Phase 6 | Pending |
| COP-06 | Phase 6 | Pending |
| MNT-01 | Phase 7 | Pending |
| MNT-02 | Phase 7 | Pending |
| MNT-03 | Phase 7 | Pending |
| MNT-04 | Phase 7 | Pending |
| MNT-05 | Phase 7 | Pending |
| CMP-01 | Phase 8 | Pending |
| CMP-02 | Phase 8 | Pending |
| CMP-03 | Phase 8 | Pending |
| CMP-04 | Phase 8 | Pending |
| LL-01 | Phase 8 | Pending |
| LL-02 | Phase 8 | Pending |
| LL-03 | Phase 8 | Pending |
| LL-04 | Phase 8 | Pending |
| UX-01 | Phase 9 | Pending |
| UX-02 | Phase 9 | Pending |
| UX-03 | Phase 10 | Pending |
| UX-04 | Phase 10 | Pending |
| UX-05 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-19*
*Last updated: 2026-07-19 fixed phase mappings*