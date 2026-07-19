# Research: Phase 2 — Expert Knowledge Copilot (RAG)

## RAG Architecture

### Retrieval-Augmented Generation Patterns
- **Naive RAG**: Simple vector similarity search → LLM generation
- **Advanced RAG**: Query rewriting, hybrid search, re-ranking
- **Modular RAG**: Separate retrieval, re-ranking, and generation modules

### Chunking Strategies for Industrial Documents
- **Fixed-size chunks**: 512-1024 tokens, simple but may split mid-concept
- **Semantic chunks**: Split at paragraph/section boundaries
- **Document-aware chunks**: Respect document structure (headers, sections)
- **Recommendation**: 768 tokens with 200 token overlap for technical docs

### Hybrid Search
- **Vector search**: Semantic similarity via embeddings
- **Keyword search**: BM25/TF-IDF for exact matches (equipment tags, codes)
- **Metadata filtering**: Filter by document type, date, equipment
- **Score fusion**: Combine vector + keyword scores with weights

## LLM Integration

### OpenAI API Patterns
```python
# RAG query with citations
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "Answer based on context. Cite sources."},
        {"role": "user", "content": f"Context: {retrieved_chunks}\n\nQuestion: {query}"}
    ]
)
```

### Confidence Score Generation
- Ask LLM to rate confidence 1-5 with each answer
- Use retrieval score as additional signal
- Calibrate confidence based on chunk relevance scores

### Prompt Engineering for Industrial Domain
- Include domain context in system prompt
- Specify response format with citations
- Ask for step-by-step reasoning for complex queries

## Source Citation

### Document Chunk Attribution
- Store metadata with each chunk: filename, page, section
- Include chunk ID in retrieval results
- Map chunk IDs back to source documents

### Citation Format
```
[1] Maintenance Manual PUMP-A101, Section 3.2, Page 15
[2] Inspection Report 2024-001, Appendix A
```

### Direct Link Generation
- Store document paths in OKF bundles
- Generate clickable links to source documents
- Include page numbers for PDF navigation

## Mobile-First UI

### Responsive Design Patterns
- **CSS Grid/Flexbox**: Layout that adapts to screen size
- **Mobile-first CSS**: Start with mobile styles, add media queries for desktop
- **Touch-friendly**: Large tap targets, swipe gestures

### PWA Patterns
- **Service Worker**: Cache static assets for offline use
- **Manifest file**: Add to home screen capability
- **IndexedDB**: Store recent queries and responses offline

### Voice Input
- **Web Speech API**: Browser-native speech recognition
- **Whisper API**: OpenAI's speech-to-text for better accuracy

## Performance Optimization

### Query Latency Target (<5 seconds)
- **Caching**: Cache frequent queries and embeddings
- **Pre-computation**: Pre-embed common queries
- **Streaming**: Stream LLM responses for better perceived performance

### Index Optimization
- **HNSW index**: Fast approximate nearest neighbor search
- **IVF index**: Good for large datasets
- **ChromaDB defaults**: Work well for hackathon scale

## Common Pitfalls

1. **Hallucination**: Always cite sources, never let LLM make up facts
2. **Context window limits**: Chunk documents properly, don't overload context
3. **Mobile performance**: Test on real devices, optimize for slow networks
4. **Offline functionality**: Service workers are complex, start with online-only
5. **Confidence calibration**: LLMs are overconfident, validate with retrieval scores
