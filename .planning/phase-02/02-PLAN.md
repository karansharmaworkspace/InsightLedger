# Plan: Phase 2 — PDF & Document Ingestion Pipeline

## Goal
Ingest PDF documents and extract text/tables from industrial documents.

## Requirement IDs
ING-01, ING-03

## Success Criteria
1. PDF text extraction using pdfplumber working
2. Table extraction from PDFs functional
3. Document metadata extraction complete
4. Basic document storage in OKF bundles
5. API endpoint for document upload operational
6. Batch ingestion support implemented

## Tasks

### Task 2.1: PDF Text Extraction
- [ ] Install pdfplumber library
- [ ] Implement PDF text extraction function
- [ ] Handle multi-page documents
- [ ] Preserve text formatting and structure

### Task 2.2: Table Extraction
- [ ] Extract tables from PDFs using pdfplumber
- [ ] Convert tables to structured data (list of dicts)
- [ ] Handle merged cells and complex layouts
- [ ] Export tables as CSV/JSON

### Task 2.3: Document Metadata
- [ ] Extract PDF metadata (author, title, dates)
- [ ] Extract page count and structure
- [ ] Generate document fingerprint (hash)
- [ ] Store metadata in database

### Task 2.4: Spreadsheet Ingestion
- [ ] Implement Excel file processing using pandas
- [ ] Implement CSV file processing
- [ ] Extract structured data from spreadsheets
- [ ] Handle multiple sheets

### Task 2.5: Document Storage
- [ ] Create OKF bundle for each document
- [ ] Store extracted text in markdown format
- [ ] Store tables as structured data
- [ ] Update log.md with ingestion record

### Task 2.6: Upload API
- [ ] Create `POST /api/ingest` endpoint
- [ ] Accept PDF file upload
- [ ] Process document asynchronously
- [ ] Return ingestion status

### Task 2.7: Batch Processing
- [ ] Create `POST /api/ingest/batch` endpoint
- [ ] Accept multiple files
- [ ] Process files in queue
- [ ] Return batch status

### Task 2.8: Error Handling
- [ ] Handle corrupted PDFs gracefully
- [ ] Handle password-protected PDFs
- [ ] Log extraction failures
- [ ] Return meaningful error messages

## Technical Design

### API Endpoints
- `POST /api/ingest` - Ingest single document
- `POST /api/ingest/batch` - Batch ingest documents
- `GET /api/documents` - List ingested documents
- `GET /api/documents/{id}` - Get document details

### Data Models
```python
class Document:
    id: str
    filename: str
    file_type: str  # pdf, xlsx, csv
    file_hash: str
    metadata: Dict[str, Any]
    created_at: datetime
    status: str  # pending, processing, completed, failed

class ExtractedContent:
    document_id: str
    text: str
    tables: List[List[Dict[str, str]]]
    page_count: int
```

### Dependencies
```txt
pdfplumber==0.10.3
pandas==2.1.3
openpyxl==3.1.2
python-multipart==0.0.6
```

## Verification

### Unit Tests
- Test PDF text extraction
- Test table extraction
- Test metadata extraction
- Test spreadsheet ingestion

### Integration Tests
- Test document upload API
- Test batch processing
- Test OKF bundle creation

### Manual Verification
- Upload sample PDF document
- Verify extracted text accuracy
- Check OKF bundle structure

## Dependencies
- Phase 1: Project Setup & Core Infrastructure

## Timeline
- Task 2.1: 1.5 hours
- Task 2.2: 1.5 hours
- Task 2.3: 1 hour
- Task 2.4: 1 hour
- Task 2.5: 1 hour
- Task 2.6: 1 hour
- Task 2.7: 1 hour
- Task 2.8: 0.5 hours
- **Total: 8.5 hours**

## Risks
1. **PDF encoding issues**: Industrial PDFs may have non-standard encoding
   - Mitigation: Use pdfplumber with fallback to OCR
2. **Complex table layouts**: Merged cells may not extract correctly
   - Mitigation: Manual review for critical documents
