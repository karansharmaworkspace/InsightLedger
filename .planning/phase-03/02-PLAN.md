# Plan: Phase 3 — OCR & Scanned Document Processing

## Goal
Process scanned documents with OCR for text extraction.

## Requirement IDs
ING-02

## Success Criteria
1. Tesseract OCR integration working
2. Image preprocessing improves OCR accuracy
3. OCR confidence scoring implemented
4. Scanned document handling pipeline functional
5. Support for multiple image formats

## Tasks

### Task 3.1: Tesseract Integration
- [ ] Install Tesseract OCR
- [ ] Install pytesseract Python wrapper
- [ ] Implement basic OCR function
- [ ] Test with sample scanned documents

### Task 3.2: Image Preprocessing
- [ ] Implement grayscale conversion
- [ ] Add noise reduction
- [ ] Implement deskewing for tilted scans
- [ ] Add contrast enhancement

### Task 3.3: OCR Pipeline
- [ ] Create OCR processing pipeline
- [ ] Handle multiple image formats (PNG, JPEG, TIFF)
- [ ] Process multi-page scanned documents
- [ ] Store OCR results with metadata

### Task 3.4: Confidence Scoring
- [ ] Extract OCR confidence scores
- [ ] Calculate average confidence per document
- [ ] Flag low-confidence documents for review
- [ ] Store confidence metrics

### Task 3.5: PDF Scanned Documents
- [ ] Detect if PDF is scanned (image-based)
- [ ] Convert PDF pages to images
- [ ] Apply OCR to each page
- [ ] Combine results into text

### Task 3.6: API Integration
- [ ] Add OCR endpoint to ingestion API
- [ ] Auto-detect scanned documents
- [ ] Route to appropriate processing pipeline
- [ ] Return OCR results

### Task 3.7: Quality Assurance
- [ ] Create OCR accuracy tests
- [ ] Benchmark against known documents
- [ ] Log processing metrics
- [ ] Generate quality reports

### Task 3.8: Error Handling
- [ ] Handle low-quality scans
- [ ] Handle rotated documents
- [ ] Log OCR failures
- [ ] Provide manual override option

## Technical Design

### API Endpoints
- `POST /api/ocr` - Process document with OCR
- `GET /api/ocr/{document_id}/confidence` - Get OCR confidence

### Data Models
```python
class OCRResult:
    document_id: str
    text: str
    confidence: float  # 0-100
    page_results: List[PageOCR]
    processing_time: float

class PageOCR:
    page_number: int
    text: str
    confidence: float
    image_path: str
```

### Dependencies
```txt
pytesseract==0.3.10
Pillow==10.1.0
opencv-python==4.8.1.78
```

## Verification

### Unit Tests
- Test image preprocessing functions
- Test OCR text extraction
- Test confidence scoring

### Integration Tests
- Test OCR pipeline end-to-end
- Test scanned PDF processing
- Test API integration

### Manual Verification
- Process sample scanned documents
- Verify OCR accuracy
- Check confidence scores

## Dependencies
- Phase 1: Project Setup & Core Infrastructure
- Phase 2: PDF & Document Ingestion Pipeline

## Timeline
- Task 3.1: 1 hour
- Task 3.2: 1 hour
- Task 3.3: 1 hour
- Task 3.4: 0.5 hours
- Task 3.5: 1 hour
- Task 3.6: 0.5 hours
- Task 3.7: 0.5 hours
- Task 3.8: 0.5 hours
- **Total: 6 hours**

## Risks
1. **OCR accuracy**: Poor scan quality reduces accuracy
   - Mitigation: Image preprocessing, confidence thresholds
2. **Processing speed**: OCR is CPU-intensive
   - Mitigation: Async processing, queue management
