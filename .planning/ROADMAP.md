# ROADMAP

## Phase 1: Wire Classification Pipeline
**Goal**: Enable the existing 3-tier classification system that's currently dead code

### Success Criteria
- ClassMemory.find_match() called in UniversalEngine.process()
- 500new.pt inference triggered for fine classification
- DINOv2 similarity used as fallback
- Classification results appear in output JSON

### Scope
- core/universal_engine.py — wire classification
- core/class_memory.py — verify working
- core/dinov2_embedder.py — verify working
- tests/ — add classification tests

---

## Phase 2: Implement Tag Number Extraction
**Goal**: Extract industrial tag numbers (V-101, P-202) from P&ID symbols

### Success Criteria
- Shape-aware OCR crops and reads tag regions
- Tags appear in node metadata
- No false readings from symbol geometry

### Scope
- core/universal_engine.py — implement _extract_labels()
- utils/ — OCR preprocessing utilities
- tests/ — OCR accuracy tests

---

## Phase 3: Process-Aware Topology
**Goal**: Distinguish process lines from signal lines and utility connections

### Success Criteria
- Line type classification (process, signal, utility)
- Connection type in output (process connection vs instrument signal)
- Instrument loop grouping

### Scope
- utils/topology_engine.py — line type detection
- core/universal_engine.py — topology integration
- utils/formatter.py — connection metadata
- tests/ — topology tests

---

## Phase 4: Complete DEXPI Output
**Goal**: Output includes design conditions, pipe specs, and instrument metadata

### Success Criteria
- Design pressure/temperature in output
- Pipe class designations
- Instrument loop assignments
- CAD-importable JSON

### Scope
- utils/formatter.py — extended schema
- core/universal_engine.py — metadata extraction
- tests/ — output validation

---

## Phase 5: Testing & Documentation
**Goal**: Bring test coverage to critical paths, fix documentation gaps

### Success Criteria
- Unit tests for core modules
- Integration tests for pipeline
- Documentation matches code
- No misleading claims in reports

### Scope
- tests/ — comprehensive test suite
- *.md — documentation updates
