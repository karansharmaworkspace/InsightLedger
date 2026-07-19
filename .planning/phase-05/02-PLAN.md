# Plan: Phase 5 — Vector Embedding & Search Infrastructure

## Goal
Set up vector search for semantic queries across the knowledge graph.

## Requirement IDs
KG-05

## Success Criteria
1. ChromaDB setup for vector storage working
2. Document chunking strategy (768 tokens, 200 overlap) implemented
3. Embedding generation using sentence-transformers working
4. Hybrid search (vector + keyword) functional
5. Metadata filtering (document type, date, equipment) working
6. Search result ranking implemented

## Tasks

### Task 5.1: ChromaDB Setup
- [ ] Install ChromaDB
- [ ] Create vector database collection
- [ ] Configure embedding model
- [ ] Test basic vector operations

### Task 5.2: Document Chunking
- [ ] Implement text chunking (768 tokens)
- [ ] Add overlap between chunks (200 tokens)
- [ ] Preserve metadata with each chunk
- [ ] Handle edge cases (short docs, tables)

### Task 5.3: Embedding Generation
- [ ] Install sentence-transformers
- [ ] Load embedding model (all-MiniLM-L6-v2)
- [ ] Generate embeddings for document chunks
- [ ] Store embeddings in ChromaDB

### Task 5.4: Vector Search
- [ ] Implement similarity search
- [ ] Add top-k retrieval
- [ ] Configure search parameters
- [ ] Test search accuracy

### Task 5.5: Keyword Search
- [ ] Implement BM25 keyword search
- [ ] Create inverted index
- [ ] Handle industrial terminology
- [ ] Combine with vector search

### Task 5.6: Hybrid Search
- [ ] Combine vector + keyword scores
- [ ] Implement weighted fusion
- [ ] Tune fusion weights
- [ ] Test hybrid search accuracy

### Task 5.7: Metadata Filtering
- [ ] Filter by document type
- [ ] Filter by date range
- [ ] Filter by equipment tag
- [ ] Combine filters with search

### Task 5.8: Search API
- [ ] Create `POST /api/search` endpoint
- [ ] Accept search query + filters
- [ ] Return ranked results
- [ ] Include relevance scores

## Technical Design

### API Endpoints
- `POST /api/search` - Search documents
- `GET /api/search/suggest` - Get search suggestions

### Data Models
```python
class SearchResult:
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: Dict[str, Any]

class SearchQuery:
    query: str
    filters: Dict[str, Any]
    top_k: int = 10
    search_type: str = "hybrid"  # vector, keyword, hybrid
```

### Dependencies
```txt
chromadb==0.4.18
sentence-transformers==2.2.2
rank-bm25==0.2.2
```

## Verification

### Unit Tests
- Test document chunking
- Test embedding generation
- Test vector search
- Test keyword search
- Test hybrid search

### Integration Tests
- Test search API end-to-end
- Test metadata filtering
- Test search accuracy

### Manual Verification
- Index sample documents
- Search for relevant content
- Verify search results quality

## Dependencies
- Phase 1: Project Setup & Core Infrastructure
- Phase 2: PDF & Document Ingestion Pipeline
- Phase 3: OCR & Scanned Document Processing
- Phase 4: Entity Extraction & OKF Knowledge Graph

## Timeline
- Task 5.1: 1 hour
- Task 5.2: 1 hour
- Task 5.3: 1 hour
- Task 5.4: 1 hour
- Task 5.5: 1 hour
- Task 5.6: 1 hour
- Task 5.7: 0.5 hours
- Task 5.8: 0.5 hours
- **Total: 7 hours**

## Risks
1. **Embedding quality**: Model may not capture industrial terminology
   - Mitigation: Fine-tune model, use domain-specific embeddings
2. **Search latency**: Large corpora may be slow
   - Mitigation: Index optimization, caching
