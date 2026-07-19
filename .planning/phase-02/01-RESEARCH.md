# Research: Phase 2 — PDF & Document Ingestion Pipeline

## PDF Text Extraction

### Libraries
- **pdfplumber**: Best for text + tables, pure Python
- **PyPDF2**: Older, less accurate
- **pdfminer.six**: Good for text extraction
- **pymupdf (fitz)**: Fast, commercial license

### Recommendation
- **pdfplumber** for text + tables (best balance)

### Table Extraction
- pdfplumber handles most table formats
- Complex layouts may need manual review
- Export as CSV/JSON for downstream processing

## Document Types

### Engineering Drawings (P&IDs)
- Mostly image-based (scanned)
- Need OCR for text extraction
- Equipment tags in specific locations

### Maintenance Records
- Usually PDFs with text + tables
- Work orders, failure reports
- Structured data in tables

### Safety Procedures
- Text-heavy PDFs
- May have images/diagrams
- Version control important

### Inspection Reports
- Mix of text and tables
- May include photos
- Timestamps critical

## Common Pitfalls

1. **PDF encoding**: Industrial PDFs may use non-standard fonts
2. **Scanned PDFs**: Image-based, need OCR
3. **Password-protected**: May need decryption
4. **Large files**: Memory management important
5. **Batch processing**: Queue management needed
