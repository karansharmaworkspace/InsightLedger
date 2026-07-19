# Industrial Knowledge Assistant

AI-powered industrial knowledge assistant for ET Hackathon 2.0. Digitizes P&IDs, ingests maintenance documents, and provides intelligent querying with compliance tracking.

## Quick Start

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload

# Run demo
python ../demo.py
```

API at `http://localhost:8000`. Dashboard at `http://localhost:8000` (serve frontend files).

## Features

- **P&ID Digitization**: OCR + topology extraction from piping diagrams
- **Document Ingestion**: PDF, Excel, CSV processing with entity extraction
- **Knowledge Graph**: Equipment relationships and dependencies
- **RAG Query Engine**: Context-aware answers with source citations
- **Maintenance Intelligence**: RCA, scheduling, spare parts tracking
- **Compliance Tracking**: ISA-5.1, OSHA, EPA standards monitoring
- **Mobile-First Chat**: Voice input, responsive design

## API Endpoints

### Core
| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/health/system` | GET | System-wide health with component status |

### Document Processing
| Endpoint | Method | Description |
|---|---|---|
| `/api/digitize` | POST | Upload P&ID image |
| `/api/ingest` | POST | Ingest document |
| `/api/ingest/batch` | POST | Batch ingest |
| `/api/documents/{id}` | GET | Get document details |

### Knowledge
| Endpoint | Method | Description |
|---|---|---|
| `/api/knowledge-graph` | GET | Knowledge graph for visualization |
| `/api/knowledge-graph/stats` | GET | Graph statistics |
| `/api/equipment` | GET | List equipment |
| `/api/equipment/{id}` | GET | Equipment details |

### Search & Query
| Endpoint | Method | Description |
|---|---|---|
| `/api/search` | GET | Search knowledge |
| `/api/search/semantic` | GET | Semantic search |
| `/api/query` | GET | RAG query with citations |

### Maintenance
| Endpoint | Method | Description |
|---|---|---|
| `/api/maintenance/tasks` | GET/POST | List/create tasks |
| `/api/maintenance/schedule` | GET | Maintenance schedule |
| `/api/maintenance/rca` | POST | Root cause analysis |
| `/api/maintenance/spare-parts` | GET/POST | Spare parts inventory |

### Compliance
| Endpoint | Method | Description |
|---|---|---|
| `/api/compliance/checks` | GET/POST | Compliance checks |
| `/api/compliance/status` | GET | Compliance status |
| `/api/compliance/lessons` | GET/POST | Lessons learned |

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── database.py             # SQLite + SQLAlchemy
│   ├── models/                 # DB models
│   ├── api/
│   │   ├── ingest.py           # Document ingestion
│   │   ├── knowledge.py        # Knowledge graph
│   │   ├── search.py           # Vector search
│   │   ├── query.py            # RAG queries
│   │   ├── maintenance.py      # Maintenance intelligence
│   │   └── compliance.py       # Compliance tracking
│   └── services/
│       ├── pid_ocr.py          # CRAFT + TrOCR (P&ID images)
│       ├── ocr_scanned.py      # Tesseract (scanned docs)
│       ├── topology_engine.py  # Line detection + ISA-5.1
│       ├── document_ingestion.py  # PDF/Excel/CSV extraction
│       ├── entity_extraction.py   # Equipment, parameters
│       ├── chunking.py         # Document chunking
│       ├── vector_search.py    # ChromaDB vectors
│       ├── knowledge_graph.py  # OKF knowledge graph
│       ├── rag_engine.py       # RAG + CAG caching
│       ├── maintenance.py      # RCA, scheduling, parts
│       ├── compliance.py       # Standards tracking
│       ├── performance.py      # Query caching
│       └── integration.py      # Health checks
├── frontend/
│   ├── index.html              # Chat interface
│   └── dashboard.html          # Knowledge graph explorer
├── storage/                    # Data storage
├── requirements.txt
└── .env
```

## Environment Variables

```bash
GROQ_API_KEY=gsk_...          # Optional: enables Llama 3.3 70B responses
```

Without Groq key, the system uses fallback responses from indexed content.

## Demo

```bash
# Start server
uvicorn app.main:app --reload

# Run automated demo
python ../demo.py
```

## Frontend

Open `frontend/index.html` in a browser for the chat interface.
Open `frontend/dashboard.html` for the knowledge graph explorer.
