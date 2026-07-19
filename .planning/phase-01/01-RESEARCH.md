# Research: Phase 1 — Document Ingestion & Knowledge Graph Foundation

## Document Ingestion Pipeline

### PDF Extraction
- **pdfplumber** (Python): Best for text + table extraction from PDFs, handles complex layouts
- **PyPDF2**: Lightweight, good for simple text extraction
- **tabula-py**: Specialized for table extraction from PDFs
- **camelot**: Another table extraction option, better for complex tables

### OCR for Scanned Documents
- **Tesseract OCR** (open source): Good baseline, works offline
- **Google Cloud Vision**: Higher accuracy for industrial documents
- **AWS Textract**: Excellent for forms and tables in scanned docs
- **PaddleOCR**: Good for multilingual documents

### P&ID Diagram Parsing
- **Computer Vision approach**: Use YOLO/Faster R-CNN for symbol detection
- **Template matching**: For standard P&ID symbols
- **OCR + NLP**: Extract text annotations and equipment tags
- **Pre-trained models**: Look for industrial diagram parsing models on HuggingFace

### Email Archive Extraction
- **email-parser** (Python): Parse EML files
- **pypff**: For PST/OST file extraction
- **Extract attachments**: Handle PDFs, images, spreadsheets embedded in emails

### Spreadsheet Processing
- **pandas**: Excel (xlsx) and CSV processing
- **openpyxl**: Excel file manipulation
- **xlrd**: Read older Excel formats

## Entity Extraction

### Equipment Tag Recognition
- Pattern: `[A-Z]+-[A-Z0-9]+` (e.g., PUMP-A101, VALVE-V201)
- Use regex + NER (Named Entity Recognition) for custom industrial tags
- Train custom NER model on industrial document corpus

### Process Parameter Extraction
- Temperature: `\d+\.?\d*\s*°[CF]`
- Pressure: `\d+\.?\d*\s*(psi|bar|kPa|MPa)`
- Flow rate: `\d+\.?\d*\s*(lpm|gpm|m³/h)`

### Regulatory Reference Detection
- Factory Act: `Section \d+` patterns
- OISD: `OISD-\d+` patterns
- PESO: `PESO/.*` patterns

## Open Knowledge Format (OKF)

### OKF v0.1 Specification
- Markdown-based knowledge bundles
- Directory structure: `bundle/concept-type/concept-id.md`
- Concept types: equipment, procedure, incident, person, document
- Cross-links: `[Concept Name](../concept-type/concept-id.md)`
- Metadata: YAML frontmatter in each markdown file

### OKF Bundle Structure for Industrial Knowledge
```
industrial-kb/
├── log.md                    # Change log
├── equipment/
│   ├── pump-a101.md
│   └── valve-v201.md
├── procedures/
│   ├── maintenance-pump-a101.md
│   └── safety-procedure-001.md
├── incidents/
│   ├── incident-2024-001.md
│   └── near-miss-2024-005.md
├── documents/
│   ├── manual-pump-a101.md
│   └── inspection-report-2024-001.md
└── persons/
    ├── john-doe.md
    └── jane-smith.md
```

### OKF Enrichment Agent Patterns
- Parse documents → extract entities → create/update OKF concepts
- Maintain cross-links between related concepts
- Update log.md with changes
- Validate OKF structure after updates

## Knowledge Graph Construction

### Graph Database Options
- **Neo4j**: Most mature, Cypher query language, good for complex relationships
- **Amazon Neptune**: Managed service, SPARQL + Gremlin support
- **NetworkX** (Python): In-memory graph, good for prototyping
- **RDFLib**: RDF-based knowledge graphs, SPARQL queries

### Recommendation for Hackathon
- Start with **NetworkX** for prototyping (fast, no setup)
- Migrate to **Neo4j** if complexity grows
- OKF provides structure, graph DB provides query capability

## Technology Stack Recommendation

### Backend
- **FastAPI**: Modern Python web framework, async support
- **Python 3.11+**: For type hints and performance
- **SQLite**: Simple storage for metadata (upgrade to PostgreSQL later)

### Document Processing
- **pdfplumber**: PDF text/table extraction
- **Tesseract**: OCR for scanned docs
- **pandas**: Spreadsheet processing
- **email-parser**: Email archive extraction

### Knowledge Graph
- **NetworkX**: In-memory graph for prototyping
- **OKF**: Structured knowledge bundles
- **ChromaDB**: Vector embeddings for semantic search

### AI/ML
- **OpenAI API**: GPT-4 for entity extraction and Q&A
- **sentence-transformers**: Local embeddings
- **spaCy**: NER and text processing

## Common Pitfalls

1. **PDF encoding issues**: Industrial PDFs often have non-standard encoding, use pdfplumber over PyPDF2
2. **P&ID parsing**: Full auto-parsing is extremely hard, start with OCR + manual annotation
3. **Entity disambiguation**: Same equipment may have different names across documents
4. **OKF adoption**: Keep bundle structure simple, don't over-engineer concept types
5. **Graph maintenance**: Start simple, add complexity only when needed
