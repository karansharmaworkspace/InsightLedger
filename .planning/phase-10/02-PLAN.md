# Plan: Phase 10 — Knowledge Graph Explorer & Dashboard

## Goal
Build interactive knowledge graph explorer with D3.js/vis.js visualization, status dashboard with real-time updates, search interface with fast results, and document viewer with preview capabilities.

## Requirement IDs
UX-03, UX-04

## Success Criteria
1. Interactive knowledge graph explorer with zoom, pan, and filter
2. Status dashboard with real-time equipment and compliance status
3. Search interface with fast results (<5 seconds)
4. Document viewer with preview capabilities
5. Responsive design works on desktop and tablet

## Tasks

### Task 10.1: Knowledge Graph Visualization
- [ ] Integrate vis.js for graph rendering
- [ ] Implement force-directed layout algorithm
- [ ] Add node click for equipment details
- [ ] Add edge hover for relationship types
- [ ] Implement zoom and pan controls

### Task 10.2: Graph Interaction Features
- [ ] Implement node selection and highlighting
- [ ] Add filter by node type (equipment, document, person)
- [ ] Add filter by relationship type
- [ ] Implement search within graph
- [ ] Add graph export (PNG, JSON)

### Task 10.3: Status Dashboard
- [ ] Create traffic light compliance widgets
- [ ] Implement equipment health progress bars
- [ ] Add trend charts for compliance over time
- [ ] Show upcoming maintenance schedule

### Task 10.4: Real-Time Updates
- [ ] Implement WebSocket connection for live updates
- [ ] Add polling fallback for WebSocket issues
- [ ] Update dashboard on knowledge graph changes
- [ ] Show update indicators

### Task 10.5: Search Interface
- [ ] Create search input with autocomplete
- [ ] Implement debounced search (300ms)
- [ ] Add faceted search (document type, date, equipment)
- [ ] Show search results with relevance scores
- [ ] Cache recent searches

### Task 10.6: Document List View
- [ ] Create sortable table view
- [ ] Implement card view with previews
- [ ] Add list view for compact display
- [ ] Implement pagination

### Task 10.7: Document Preview
- [ ] Integrate PDF.js for PDF viewing
- [ ] Add image viewer for diagrams
- [ ] Show document metadata
- [ ] Implement zoom and pan for documents

### Task 10.8: Navigation and Breadcrumbs
- [ ] Implement breadcrumb navigation
- [ ] Add back button functionality
- [ ] Create search within document feature
- [ ] Implement document history

## Technical Design

### API Endpoints
- `GET /api/graph` - Get knowledge graph data
- `GET /api/graph/{node_id}` - Get node details
- `GET /api/graph/edges/{node_id}` - Get node connections
- `GET /api/search` - Search documents and equipment
- `GET /api/documents/{id}/preview` - Get document preview

### Data Models
```python
class GraphNode:
    id: str
    type: str  # equipment, document, person, standard
    label: str
    properties: Dict[str, Any]

class GraphEdge:
    source: str
    target: str
    type: str  # requires, inspects, uses, etc.
    properties: Dict[str, Any]
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── KnowledgeGraph/
│   │   │   ├── GraphExplorer.jsx
│   │   │   ├── GraphCanvas.jsx
│   │   │   ├── GraphControls.jsx
│   │   │   └── NodeDetails.jsx
│   │   ├── Dashboard/
│   │   │   ├── StatusDashboard.jsx
│   │   │   ├── ComplianceWidget.jsx
│   │   │   └── MaintenanceWidget.jsx
│   │   ├── Search/
│   │   │   ├── SearchInterface.jsx
│   │   │   ├── SearchResults.jsx
│   │   │   └── FacetFilters.jsx
│   │   └── DocumentViewer/
│   │       ├── DocumentList.jsx
│   │       ├── DocumentPreview.jsx
│   │       └── PdfViewer.jsx
```

## Verification

### Unit Tests
- Test graph node rendering
- Test graph interaction events
- Test search functionality
- Test document preview

### Integration Tests
- Test graph visualization end-to-end
- Test search with real data
- Test document preview with sample PDFs

### Manual Verification
- View knowledge graph with sample data
- Test zoom, pan, and filter
- Search for equipment and documents
- Preview PDF documents

## Dependencies
- Phase 4: Entity Extraction & OKF Knowledge Graph
- Phase 9: Mobile-First Chat Interface

## Timeline
- Task 10.1: 2 hours
- Task 10.2: 1.5 hours
- Task 10.3: 1.5 hours
- Task 10.4: 1 hour
- Task 10.5: 1.5 hours
- Task 10.6: 1 hour
- Task 10.7: 1 hour
- Task 10.8: 0.5 hours
- **Total: 10 hours**

## Risks
1. **Graph performance with large datasets**: Too many nodes slow rendering
   - Mitigation: Virtual scrolling, limit visible nodes, clustering
2. **PDF.js limitations**: Some PDFs may not render correctly
   - Mitigation: Fallback to image conversion, error handling
3. **Search latency**: Complex queries may be slow
   - Mitigation: Cache results, optimize queries, progressive loading
