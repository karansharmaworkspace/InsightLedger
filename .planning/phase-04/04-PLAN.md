# Plan: Phase 4 — Compliance Intelligence & Lessons Learned

## Goal
Two AI agents working together:
1. Compliance Intelligence: Maps regulatory requirements against current procedures, equipment states, and inspection records to identify compliance gaps
2. Lessons Learned Engine: Analyses incident reports, near-miss records, audit findings, and quality non-conformances to identify systemic patterns

## Requirement IDs
CMP-01, CMP-02, CMP-03, CMP-04, LL-01, LL-02, LL-03, LL-04

## Success Criteria
1. System maps regulatory requirements (Factory Act, OISD, PESO) against current procedures
2. System identifies compliance gaps between requirements and current state
3. System can auto-generate compliance evidence packages for audits
4. System flags quality deviations before they escalate
5. Agent analyses incident reports and near-miss records
6. Agent analyses audit findings and quality non-conformances
7. Agent identifies systemic patterns invisible to individual review
8. Agent proactively pushes warnings to operational teams before similar conditions recur

## Tasks

### Task 4.1: Regulatory Knowledge Base
- [ ] Create OKF concepts for Factory Act provisions
- [ ] Create OKF concepts for OISD standards
- [ ] Create OKF concepts for PESO regulations
- [ ] Structure requirements for automated matching

### Task 4.2: Compliance Gap Analysis Engine
- [ ] Map procedures to regulatory requirements
- [ ] Check equipment inspection status
- [ ] Verify maintenance compliance
- [ ] Calculate compliance scores

### Task 4.3: Evidence Package Generator
- [ ] Collect relevant documents for audit
- [ ] Generate compliance evidence report
- [ ] Create gap analysis document
- [ ] Format for regulatory submission

### Task 4.4: Incident Analysis Agent
- [ ] Categorize incident reports (safety, quality, environmental)
- [ ] Extract root causes from incidents
- [ ] Identify contributing factors
- [ ] Generate incident summaries

### Task 4.5: Pattern Detection Engine
- [ ] Detect temporal patterns (time-based trends)
- [ ] Identify equipment-specific patterns
- [ ] Find human factor patterns
- [ ] Detect systemic process issues

### Task 4.6: Proactive Warning System
- [ ] Monitor conditions that match past incidents
- [ ] Calculate risk scores based on historical patterns
- [ ] Generate warnings before similar conditions recur
- [ ] Prioritize warnings by severity

### Task 4.7: Compliance Dashboard
- [ ] Show overall compliance status (traffic lights)
- [ ] Display compliance trends over time
- [ ] Show gap analysis results
- [ ] List pending compliance actions

### Task 4.8: Lessons Learned Interface
- [ ] Display incident patterns
- [ ] Show systemic issues identified
- [ ] List proactive warnings
- [ ] Provide recommendations

## Technical Design

### API Endpoints
- `GET /api/compliance/status` - Get compliance status
- `GET /api/compliance/gaps` - Get compliance gaps
- `POST /api/compliance/evidence` - Generate evidence package
- `GET /api/lessons/incidents` - Get incident analysis
- `GET /api/lessons/patterns` - Get detected patterns
- `GET /api/lessons/warnings` - Get proactive warnings

### Data Models
```python
class RegulatoryRequirement:
    id: str
    standard: str  # Factory Act, OISD, PESO
    section: str
    description: str
    requirements: List[str]

class ComplianceGap:
    requirement_id: str
    current_state: str
    required_state: str
    severity: str  # critical, major, minor, observation
    evidence: List[str]

class IncidentReport:
    id: str
    date: date
    category: str  # safety, quality, environmental, equipment
    description: str
    root_cause: str
    contributing_factors: List[str]
    actions_taken: List[str]
```

## Verification

### Unit Tests
- Test regulatory requirement matching
- Test compliance gap calculation
- Test incident categorization
- Test pattern detection

### Integration Tests
- Test compliance analysis end-to-end
- Test evidence package generation
- Test proactive warning generation

### Manual Verification
- View compliance dashboard
- Generate evidence package for test audit
- Verify incident pattern detection

## Dependencies
- Phase 1: Document Ingestion & Knowledge Graph Foundation
- Phase 2: Expert Knowledge Copilot (RAG)
- Phase 3: Maintenance Intelligence & RCA

## Timeline
- Task 4.1: 4 hours
- Task 4.2: 5 hours
- Task 4.3: 4 hours
- Task 4.4: 4 hours
- Task 4.5: 5 hours
- Task 4.6: 4 hours
- Task 4.7: 3 hours
- Task 4.8: 3 hours
- **Total: 32 hours**

## Risks
1. **Regulatory interpretation ambiguity**: Requirements can be unclear
   - Mitigation: Use LLM to interpret requirements, manual review
2. **False positives**: Overly sensitive gap detection
   - Mitigation: Confidence thresholds, human review for critical gaps
3. **Pattern noise**: Random variation vs. real patterns
   - Mitigation: Statistical significance testing, minimum sample sizes
