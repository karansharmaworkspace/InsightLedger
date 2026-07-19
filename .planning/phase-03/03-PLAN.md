# Plan: Phase 3 — Maintenance Intelligence & RCA Agent

## Goal
AI agent that fuses work order history, equipment failure records, OEM manuals, inspection findings, and real-time operating conditions for predictive maintenance recommendations and Root Cause Analysis support.

## Requirement IDs
MNT-01, MNT-02, MNT-03, MNT-04, MNT-05

## Success Criteria
1. Agent fuses work order history with equipment failure records
2. Agent incorporates OEM manuals and inspection findings
3. Agent generates predictive maintenance recommendations
4. Agent provides Root Cause Analysis (RCA) support
5. Agent generates optimized maintenance schedules

## Tasks

### Task 3.1: Maintenance Data Models
- [ ] Define work order data structure
- [ ] Define equipment failure taxonomy
- [ ] Define inspection record structure
- [ ] Create OKF concepts for maintenance data

### Task 3.2: Maintenance Data Integration
- [ ] Ingest work order history from OKF bundles
- [ ] Ingest equipment failure records
- [ ] Ingest OEM manual sections
- [ ] Ingest inspection findings

### Task 3.3: Predictive Maintenance Engine
- [ ] Implement trend detection for equipment health
- [ ] Calculate remaining useful life (RUL) estimates
- [ ] Generate maintenance recommendations
- [ ] Prioritize recommendations by risk

### Task 3.4: Root Cause Analysis Agent
- [ ] Implement 5-Why analysis automation
- [ ] Generate fishbone diagram data
- [ ] Map causes to categories (Man, Machine, Method, etc.)
- [ ] Calculate confidence scores for RCA

### Task 3.5: Maintenance Schedule Optimizer
- [ ] Analyze historical maintenance patterns
- [ ] Optimize maintenance windows
- [ ] Balance preventive vs. corrective maintenance
- [ ] Generate optimized schedules

### Task 3.6: Agent Tool-Calling System
- [ ] Define tools for data retrieval
- [ ] Implement multi-step reasoning
- [ ] Add tool execution and result handling
- [ ] Implement error handling and fallbacks

### Task 3.7: Maintenance Dashboard
- [ ] Show upcoming maintenance schedule
- [ ] Display equipment health trends
- [ ] Show predictive maintenance recommendations
- [ ] Display RCA results

### Task 3.8: Alert System
- [ ] Generate alerts for critical equipment
- [ ] Send notifications for overdue maintenance
- [ ] Warn about predicted failures
- [ ] Alert for similar failure patterns

## Technical Design

### Project Structure
```
backend/
├── app/
│   ├── services/
│   │   ├── maintenance.py    # Maintenance data service
│   │   ├── prediction.py     # Predictive maintenance engine
│   │   ├── rca.py            # Root cause analysis agent
│   │   └── scheduler.py      # Maintenance schedule optimizer
│   └── api/
│       └── maintenance.py    # Maintenance API endpoints
frontend/
├── src/
│   ├── components/
│   │   ├── MaintenanceDashboard.jsx
│   │   ├── EquipmentHealth.jsx
│   │   └── RCAPanel.jsx
```

### API Endpoints
- `GET /api/maintenance/schedule` - Get maintenance schedule
- `GET /api/maintenance/predictions` - Get predictive recommendations
- `POST /api/maintenance/rca` - Generate RCA for incident
- `GET /api/maintenance/equipment/{id}/health` - Get equipment health

### Data Models
```python
class WorkOrder:
    id: str
    equipment_id: str
    type: str  # preventive, corrective, predictive
    priority: str  # low, medium, high, critical
    status: str  # open, in-progress, completed
    created_date: date
    completed_date: Optional[date]
    technician: str
    description: str
    tasks: List[str]
    parts_used: List[str]
    time_spent_hours: float

class FailureRecord:
    id: str
    equipment_id: str
    failure_mode: str
    failure_cause: str
    failure_effect: str
    date: date
    downtime_hours: float
    cost: float
```

## Verification

### Unit Tests
- Test maintenance data models
- Test predictive maintenance calculations
- Test RCA generation
- Test schedule optimization

### Integration Tests
- Test maintenance data integration
- Test agent tool-calling
- Test alert generation

### Manual Verification
- View maintenance dashboard
- Generate RCA for test incident
- Verify predictive recommendations

## Dependencies
- Phase 1: Document Ingestion & Knowledge Graph Foundation
- Phase 2: Expert Knowledge Copilot (RAG)

## Timeline
- Task 3.1: 3 hours
- Task 3.2: 4 hours
- Task 3.3: 5 hours
- Task 3.4: 5 hours
- Task 3.5: 4 hours
- Task 3.6: 4 hours
- Task 3.7: 3 hours
- Task 3.8: 2 hours
- **Total: 30 hours**

## Risks
1. **Insufficient training data**: Industrial failure data is rare
   - Mitigation: Use synthetic data for prototyping
2. **RCA oversimplification**: Complex failures have multiple causes
   - Mitigation: Present multiple potential causes with confidence scores
3. **Alert fatigue**: Too many warnings reduce effectiveness
   - Mitigation: Smart filtering, prioritize critical alerts
