# Research: Phase 4 — Entity Extraction & OKF Knowledge Graph

## Entity Extraction

### Equipment Tags
- Pattern: `[A-Z]{2,4}-[A-Z0-9]{2,6}` (e.g., PUMP-A101)
- Variations: P-101, VLV-B202, COMP-C301
- Use regex + NER for robustness

### Process Parameters
- Temperature: `(\d+\.?\d*)\s*°?[CF]`
- Pressure: `(\d+\.?\d*)\s*(psi|bar|kPa|MPa)`
- Flow: `(\d+\.?\d*)\s*(lpm|gpm|m3/h)`

### Regulatory References
- Factory Act: `Section\s+(\d+)`
- OISD: `OISD-(\d+)`
- PESO: `PESO\s*(Regulation|Code)\s*(\d+)`

## NER Models

### spaCy
- Pre-trained models available
- Custom entity training
- Fast inference

### Hugging Face Transformers
- BERT-based NER models
- Better accuracy
- Slower inference

### Recommendation
- **spaCy** for speed
- **Transformers** for accuracy

## OKF Bundle Structure

### Concept Types
- **Equipment**: Pumps, valves, compressors
- **Procedures**: Maintenance, startup, shutdown
- **Incidents**: Failures, near-misses
- **Standards**: Factory Act, OISD, PESO

### Cross-Linking
- Equipment → Documents (manuals, reports)
- Equipment → Procedures (maintenance steps)
- Incidents → Equipment (affected assets)
- Standards → Equipment (compliance requirements)

## Common Pitfalls

1. **Entity disambiguation**: Same equipment, different names
2. **Nested entities**: Equipment within equipment
3. **Context dependence**: "PUMP" vs "PUMP-A101"
4. **Missing entities**: Incomplete extraction
5. **False positives**: Over-extraction
