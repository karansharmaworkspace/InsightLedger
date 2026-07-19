# Research: Phase 6 — RAG Query Engine & CAG Caching

## RAG Architecture Patterns

### Naive RAG vs Advanced RAG
- **Naive RAG**: Simple vector similarity → LLM generation
- **Advanced RAG**: Query rewriting, hybrid search, re-ranking
- **Modular RAG**: Separate retrieval, re-ranking, and generation modules

### Query Rewriting for Industrial Domain
- **Synonym expansion**: "pump" → "pump, centrifugal pump, pump unit"
- **Technical term normalization**: "PSI" → "pounds per square inch"
- **Context-aware rewriting**: Add equipment type context

### Retrieval Strategies
- **Top-k retrieval**: Return top 5-10 most relevant chunks
- **MMR (Maximal Marginal Relevance)**: Balance relevance and diversity
- **Hybrid retrieval**: Combine vector + keyword + metadata

## CAG (Cached-Augmented Generation) Patterns

### Cache Key Structure
```python
cache_key = f"{hash(query)}:{hash(context_window)}:{model_version}"
```

### Cache Invalidation Strategies
- **Time-based**: Invalidate after X hours
- **Event-based**: Invalidate on knowledge graph updates
- **LRU (Least Recently Used)**: Evict old entries
- **Size-based**: Limit cache size, evict oldest

### Cache Hit Optimization
- **Exact match**: Same query + context
- **Fuzzy match**: Similar queries with same intent
- **Partial match**: Cache retrieval results separately

### Cache Storage Options
- **Redis**: Persistent, distributed, fast
- **In-memory dict**: Simple, fast, ephemeral
- **SQLite**: Persistent, simple, single-user
- **Memcached**: Distributed, volatile

## Confidence Score System

### Multi-Signal Confidence
```python
confidence = (
    retrieval_score * 0.3 +  # How relevant is the retrieved context
    llm_confidence * 0.4 +   # LLM self-assessment
    source_agreement * 0.2 + # Do sources agree
    query_complexity * 0.1   # Simple queries = higher confidence
)
```

### Confidence Calibration
- **Over-confidence correction**: LLMs tend to be overconfident
- **Historical accuracy**: Track past confidence vs. actual accuracy
- **Domain-specific calibration**: Industrial queries may need different thresholds

## Source Citation System

### Citation Format
```
[1] Maintenance Manual PUMP-A101, Section 3.2, Page 15
[2] Inspection Report 2024-001, Appendix A
[3] OISD-116, Section 4.3.2
```

### Citation Metadata
- Document title
- Section/header
- Page number
- File path
- Last modified date

### Direct Link Generation
- OKF bundle paths
- PDF page anchors
- Section headers for navigation

## Performance Optimization

### Response Streaming
```python
async def stream_response(query):
    async for chunk in llm.stream(query):
        yield chunk
```

### Query Result Pagination
- **Offset/limit**: For large result sets
- **Cursor-based**: For real-time updates
- **Infinite scroll**: For mobile UX

### Response Compression
- **Gzip**: Standard compression
- **Brotli**: Better compression ratio
- **Selective compression**: Only compress large responses

## Common Pitfalls

1. **Cache invalidation complexity**: When to invalidate is hard
2. **Stale cache**: Serving outdated answers
3. **Cache thrashing**: Too many invalidations
4. **Memory leaks**: Unbounded cache growth
5. **Cold start**: First query always slow
