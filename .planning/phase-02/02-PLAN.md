# Plan: Phase 2 — Expert Knowledge Copilot (RAG + CAG)

## Goal
Build RAG + CAG (Cached-Augmented Generation) conversational AI that answers operational, maintenance, and engineering queries with fast response times, source citations, confidence scores, and direct links to originating documents.

## Requirement IDs
COP-01, COP-02, COP-03, COP-04, COP-05, COP-06

## Success Criteria
1. RAG-powered conversational AI answers operational queries across full document corpus
2. CAG caching layer provides instant responses for frequent queries
3. Responses include source citations with direct links to originating documents
4. Responses include confidence scores for answer quality
5. Interface works on mobile devices for field technicians
6. System handles maintenance and engineering domain questions
7. System provides time-to-answer improvement versus traditional search

## Tasks

### Task 2.1: Vector Embedding Pipeline
- [ ] Set up ChromaDB for vector storage
- [ ] Implement document chunking strategy (768 tokens with 200 overlap)
- [ ] Generate embeddings using sentence-transformers
- [ ] Index OKF knowledge graph documents

### Task 2.2: Hybrid Search Engine
- [ ] Implement vector similarity search
- [ ] Add keyword search (BM25)
- [ ] Implement metadata filtering (document type, date, equipment)
- [ ] Combine scores with weighted fusion

### Task 2.3: RAG Query Engine
- [ ] Implement query rewriting for industrial domain
- [ ] Retrieve relevant chunks using hybrid search
- [ ] Generate answers using OpenAI GPT-4
- [ ] Include source citations in responses

### Task 2.4: Confidence Score System
- [ ] Calculate retrieval relevance scores
- [ ] Ask LLM to rate confidence 1-5
- [ ] Combine retrieval + LLM confidence
- [ ] Calibrate confidence based on historical accuracy

### Task 2.5: Source Citation System
- [ ] Store metadata with each chunk (filename, page, section)
- [ ] Generate clickable links to source documents
- [ ] Format citations consistently
- [ ] Include page numbers for PDF navigation

### Task 2.6: Mobile-First Chat Interface
- [ ] Build React chat UI with responsive design
- [ ] Implement touch-friendly input
- [ ] Add voice input using Web Speech API
- [ ] Optimize for slow networks

### Task 2.7: Offline Support (PWA)
- [ ] Set up service worker for static assets
- [ ] Implement manifest for add-to-home-screen
- [ ] Cache recent queries in IndexedDB
- [ ] Handle offline gracefully

### Task 2.8: CAG Caching Layer
- [ ] Design cache key structure (query hash + context)
- [ ] Implement Redis/in-memory cache for query responses
- [ ] Add cache invalidation on knowledge graph updates
- [ ] Implement cache hit/miss metrics
- [ ] Pre-cache common industrial queries

### Task 2.9: Performance Optimization
- [ ] Stream LLM responses for better UX
- [ ] Optimize index for fast retrieval
- [ ] Implement query result pagination
- [ ] Add response compression

## Technical Design

### Project Structure
```
backend/
├── app/
│   ├── main.py
│   ├── services/
│   │   ├── embedding.py      # Vector embedding service
│   │   ├── search.py         # Hybrid search engine
│   │   ├── rag.py            # RAG query engine
│   │   └── citation.py       # Source citation service
│   └── api/
│       └── copilot.py        # Copilot API endpoints
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.jsx
│   │   ├── MessageBubble.jsx
│   │   └── SourceCard.jsx
│   └── services/
│       └── api.js
```

### API Endpoints
- `POST /api/copilot/query` - Ask a question (returns cached if available)
- `GET /api/copilot/history` - Get query history
- `POST /api/copilot/feedback` - Submit feedback on answers
- `GET /api/copilot/cache/stats` - Get cache statistics
- `POST /api/copilot/cache/invalidate` - Invalidate cache entries

### Dependencies
```txt
# Backend additions
chromadb==0.4.18
sentence-transformers==2.2.2
openai==1.3.7
rank-bm25==0.2.2
redis==5.0.1  # For CAG caching (or use in-memory)

# Frontend
react==18.2.0
react-dom==18.2.0
tailwindcss==3.3.5
```

## Verification

### Unit Tests
- Test document chunking
- Test embedding generation
- Test hybrid search
- Test confidence score calculation

### Integration Tests
- Test RAG query end-to-end
- Test citation accuracy
- Test mobile responsiveness

### Manual Verification
- Ask maintenance-related questions
- Verify source citations are accurate
- Test on mobile devices
- Measure query response time (<5 seconds)

## Dependencies
- Phase 1: Document Ingestion & Knowledge Graph Foundation

## Timeline
- Task 2.1: 4 hours
- Task 2.2: 4 hours
- Task 2.3: 4 hours
- Task 2.4: 3 hours
- Task 2.5: 3 hours
- Task 2.6: 4 hours
- Task 2.7: 3 hours
- Task 2.8: 3 hours
- Task 2.9: 2 hours
- **Total: 30 hours**

## Risks
1. **Hallucination**: LLM may generate false information
   - Mitigation: Always cite sources, validate with retrieval scores
2. **Context window limits**: Large documents may exceed context
   - Mitigation: Proper chunking, selective retrieval
3. **Mobile performance**: Older devices may struggle
   - Mitigation: Progressive enhancement, lazy loading
