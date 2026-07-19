# Plan: Phase 6 — RAG Query Engine & CAG Caching

## Goal
Build RAG + CAG (Cached-Augmented Generation) conversational AI that answers operational, maintenance, and engineering queries with fast response times, source citations, confidence scores, and direct links to originating documents.

## Requirement IDs
COP-01, COP-02, COP-03, COP-06

## Success Criteria
1. RAG-powered conversational AI answers operational queries across full document corpus
2. CAG caching layer provides instant responses for frequent queries
3. Responses include source citations with direct links to originating documents
4. Responses include confidence scores for answer quality
5. System handles maintenance and engineering domain questions
6. System provides time-to-answer improvement versus traditional search

## Tasks

### Task 6.1: Query Rewriting Engine
- [ ] Implement synonym expansion for industrial terms
- [ ] Add technical term normalization
- [ ] Create context-aware query rewriting
- [ ] Test with sample industrial queries

### Task 6.2: Advanced Retrieval System
- [ ] Implement top-k retrieval with configurable k
- [ ] Add MMR (Maximal Marginal Relevance) for diversity
- [ ] Implement hybrid retrieval (vector + keyword + metadata)
- [ ] Optimize retrieval speed

### Task 6.3: CAG Caching Layer
- [ ] Design cache key structure (query hash + context)
- [ ] Implement Redis/in-memory cache
- [ ] Add cache invalidation on knowledge graph updates
- [ ] Implement LRU eviction policy
- [ ] Add cache hit/miss metrics

### Task 6.4: RAG Query Engine
- [ ] Integrate with OpenAI GPT-4
- [ ] Implement prompt engineering for industrial domain
- [ ] Add response streaming for better UX
- [ ] Implement error handling and fallbacks

### Task 6.5: Source Citation System
- [ ] Store metadata with each chunk (filename, page, section)
- [ ] Generate clickable links to source documents
- [ ] Format citations consistently
- [ ] Include page numbers for PDF navigation

### Task 6.6: Confidence Score System
- [ ] Calculate retrieval relevance scores
- [ ] Ask LLM to rate confidence 1-5
- [ ] Combine retrieval + LLM confidence
- [ ] Calibrate confidence based on historical accuracy

### Task 6.7: Query History & Feedback
- [ ] Store query history in database
- [ ] Implement feedback collection (thumbs up/down)
- [ ] Use feedback to improve retrieval
- [ ] Generate query analytics

### Task 6.8: Performance Optimization
- [ ] Optimize index for fast retrieval
- [ ] Implement query result pagination
- [ ] Add response compression
- [ ] Profile and optimize slow queries

## Technical Design

### API Endpoints
- `POST /api/copilot/query` - Ask a question (returns cached if available)
- `GET /api/copilot/history` - Get query history
- `POST /api/copilot/feedback` - Submit feedback on answers
- `GET /api/copilot/cache/stats` - Get cache statistics
- `POST /api/copilot/cache/invalidate` - Invalidate cache entries

### Dependencies
```txt
chromadb==0.4.18
sentence-transformers==2.2.2
openai==1.3.7
rank-bm25==0.2.2
redis==5.0.1
```

## Verification

### Unit Tests
- Test query rewriting
- Test retrieval accuracy
- Test cache hit/miss
- Test confidence calculation

### Integration Tests
- Test RAG query end-to-end
- Test citation accuracy
- Test cache invalidation

### Manual Verification
- Ask maintenance-related questions
- Verify source citations are accurate
- Measure query response time (<5 seconds)

## Dependencies
- Phase 4: Entity Extraction & OKF Knowledge Graph
- Phase 5: Vector Embedding & Search Infrastructure

## Timeline
- Task 6.1: 1.5 hours
- Task 6.2: 2 hours
- Task 6.3: 2 hours
- Task 6.4: 2 hours
- Task 6.5: 1.5 hours
- Task 6.6: 1.5 hours
- Task 6.7: 1 hour
- Task 6.8: 1 hour
- **Total: 12.5 hours**

## Risks
1. **Cache invalidation complexity**: When to invalidate is hard
   - Mitigation: Event-based invalidation on knowledge graph updates
2. **Stale cache**: Serving outdated answers
   - Mitigation: Time-based expiration, manual invalidation
3. **LLM hallucination**: May generate false information
   - Mitigation: Always cite sources, validate with retrieval scores
