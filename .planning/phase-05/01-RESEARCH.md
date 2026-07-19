# Research: Phase 5 — Vector Embedding & Search Infrastructure

## Vector Databases

### ChromaDB
- Lightweight, easy to use
- Good for prototyping
- Limited scalability

### Pinecone
- Managed service
- High scalability
- Cost increases with usage

### Weaviate
- Open source
- GraphQL API
- Good for complex queries

### Recommendation
- **ChromaDB** for hackathon (simple, fast setup)

## Embedding Models

### sentence-transformers
- `all-MiniLM-L6-v2`: Fast, good quality
- `all-mpnet-base-v2`: Better quality, slower
- `paraphrase-mpnet-base-v2`: Best for paraphrases

### OpenAI Embeddings
- `text-embedding-ada-002`: High quality
- Requires API key
- Cost per token

### Recommendation
- **all-MiniLM-L6-v2** for speed + quality balance

## Chunking Strategies

### Fixed-Size
- Simple, predictable
- May split mid-sentence

### Semantic
- Split at sentence/paragraph boundaries
- Better context preservation

### Recommendation
- **768 tokens, 200 overlap** (good balance)

## Hybrid Search

### Vector Search
- Semantic similarity
- Handles synonyms well

### Keyword Search (BM25)
- Exact term matching
- Good for specific equipment tags

### Fusion
- Weighted combination
- Tune weights based on query type

## Common Pitfalls

1. **Embedding quality**: Model may not understand domain terms
2. **Chunk size**: Too small = lost context, too large = diluted
3. **Index size**: Large corpora need optimization
4. **Search latency**: Real-time requirements
5. **Metadata filtering**: Complex filter combinations
