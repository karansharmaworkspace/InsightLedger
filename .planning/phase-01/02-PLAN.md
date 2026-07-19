# Plan: Phase 1 — Document Ingestion & Knowledge Graph Foundation

## Goal
Build the data pipeline that ingests heterogeneous industrial documents and constructs a unified knowledge graph using Open Knowledge Format (OKF) bundles.

## Requirement IDs
ING-01, ING-02, ING-03, ING-04, ING-05, ING-06, KG-01, KG-02, KG-03, KG-04, KG-05

## Success Criteria
1. PDF documents ingested and text extracted
2. Scanned documents processed with OCR
3. Spreadsheets (Excel, CSV) ingested with structured data
4. Email archives extracted with attachments
5. P&ID diagrams parsed with equipment tags extracted
6. Entities extracted: equipment tags, process parameters, regulatory references, personnel, dates
7. Unified knowledge graph built using OKF bundles
8. Knowledge graph updates automatically when new documents arrive
9. Document-to-entity relationships maintained
10. Entity-to-entity relationships maintained
11. Knowledge graph is queryable via structured queries

## Tasks

### Task 1.1: Project Setup
- [ ] Initialize Python project with virtual environment
- [ ] Set up FastAPI backend structure
- [ ] Configure database (SQLite for metadata)
- [ ] Set up OKF bundle directory structure

### Task 1.2: PDF Ingestion Pipeline
- [ ] Implement PDF text extraction using pdfplumber
- [ ] Handle multi-page documents
- [ ] Extract tables from PDFs
- [ ] Store extracted content with metadata

### Task 1.3: OCR Pipeline
- [ ] Integrate Tesseract OCR for scanned documents
- [ ] Implement image preprocessing for better OCR accuracy
- [ ] Handle different document orientations
- [ ] Store OCR results with confidence scores

### Task 1.4: Spreadsheet Ingestion
- [ ] Implement Excel file processing using pandas
- [ ] Implement CSV file processing
- [ ] Extract structured data from spreadsheets
- [ ] Handle multiple sheets and complex formats

### Task 1.5: Email Archive Ingestion
- [ ] Implement EML file parsing
- [ ] Extract email metadata (sender, date, subject)
- [ ] Extract email body and attachments
- [ ] Process attached PDFs and spreadsheets

### Task 1.6: Entity Extraction
- [ ] Implement equipment tag recognition using regex patterns
- [ ] Extract process parameters (temperature, pressure, flow rates)
- [ ] Detect regulatory references (Factory Act, OISD, PESO)
- [ ] Extract personnel names and dates

### Task 1.7: OKF Knowledge Graph
- [ ] Design OKF bundle structure for industrial knowledge
- [ ] Implement OKF concept creation (equipment, procedures, incidents)
- [ ] Implement cross-linking between concepts
- [ ] Maintain log.md for change tracking

### Task 1.8: Knowledge Graph Query API
- [ ] Implement query endpoints for knowledge graph
- [ ] Support structured queries (type, tags, links)
- [ ] Implement graph traversal queries
- [ ] Add search functionality across knowledge graph

## Technical Design

### Project Structure
```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models/              # Data models
│   ├── services/            # Business logic
│   │   ├── ingestion/       # Document ingestion services
│   │   ├── extraction/      # Entity extraction
│   │   └── knowledge_graph/ # OKF knowledge graph
│   ├── api/                 # API endpoints
│   └── utils/               # Utilities
├── data/                    # OKF bundles storage
├── tests/                   # Test files
└── requirements.txt         # Python dependencies
```

### OKF Bundle Structure
```
data/
├── industrial-kb/
│   ├── log.md
│   ├── equipment/
│   ├── procedures/
│   ├── incidents/
│   ├── documents/
│   └── persons/
```

### API Endpoints
- `POST /api/ingest` - Ingest a document
- `GET /api/documents` - List all documents
- `GET /api/knowledge-graph` - Query knowledge graph
- `GET /api/equipment/{id}` - Get equipment details
- `GET /api/search` - Search across knowledge graph

### Dependencies
```txt
fastapi==0.104.1
uvicorn==0.24.0
pdfplumber==0.10.3
pytesseract==0.3.10
pandas==2.1.3
openpyxl==3.1.2
networkx==3.2.1
python-multipart==0.0.6
```

## Verification

### Unit Tests
- Test PDF text extraction
- Test OCR processing
- Test spreadsheet ingestion
- Test entity extraction patterns
- Test OKF bundle creation

### Integration Tests
- Test document ingestion pipeline end-to-end
- Test knowledge graph updates
- Test query API responses

### Manual Verification
- Ingest sample PDF documents
- Verify extracted text accuracy
- Check OKF bundle structure
- Query knowledge graph for test equipment

## Dependencies
- None (first phase)

## Timeline
- Task 1.1: 2 hours
- Task 1.2: 4 hours
- Task 1.3: 4 hours
- Task 1.4: 3 hours
- Task 1.5: 3 hours
- Task 1.6: 4 hours
- Task 1.7: 4 hours
- Task 1.8: 3 hours
- **Total: 27 hours**

## Risks
1. **PDF encoding issues**: Industrial PDFs may have non-standard encoding
   - Mitigation: Use pdfplumber, fallback to OCR
2. **P&ID parsing complexity**: Full auto-parsing is extremely hard
   - Mitigation: Start with OCR + manual annotation
3. **Entity disambiguation**: Same equipment may have different names
   - Mitigation: Use fuzzy matching and manual review
