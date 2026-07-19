# Industrial Knowledge Assistant

AI-powered industrial knowledge assistant for ET Hackathon 2.0. Digitizes P&IDs, ingests maintenance documents, and provides intelligent querying with compliance tracking.

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

API at `http://localhost:8000`. Chat at `http://localhost:8000/`. Dashboard at `http://localhost:8000/dashboard`.

## Features

- **P&ID Digitization**: YOLO + SAHI detection with 32 P&ID classes
- **Document Ingestion**: PDF, Excel, CSV processing
- **Knowledge Graph**: Equipment relationships and dependencies
- **RAG Query Engine**: Groq Llama 3.3 70B with source citations
- **Maintenance Intelligence**: RCA, scheduling, spare parts tracking
- **Compliance Tracking**: ISA-5.1, OSHA, EPA standards monitoring

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Chat interface |
| `/dashboard` | GET | Knowledge graph explorer |
| `/health` | GET | Health check |
| `/api/digitize` | POST | Upload P&ID image |
| `/api/ingest` | POST | Ingest document |
| `/api/knowledge-graph` | GET | Knowledge graph |
| `/api/equipment` | GET | List equipment |
| `/api/search` | GET | Search knowledge |
| `/api/query` | GET | RAG query |
| `/api/maintenance/work-orders` | GET/POST | Work orders |
| `/api/maintenance/rca` | POST | Root cause analysis |
| `/api/compliance/status` | GET | Compliance status |
| `/api/compliance/lessons` | GET/POST | Lessons learned |

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── database.py          # SQLite + SQLAlchemy
│   ├── models/              # DB models (6 files)
│   ├── api/                 # Route handlers (6 files)
│   └── services/            # Business logic (16 files)
├── frontend/
│   ├── index.html           # Chat interface
│   └── dashboard.html       # Knowledge graph explorer
├── models/                  # Put 32classes.pt here
├── data/                    # Sample data
├── requirements.txt
├── .env                     # GROQ_API_KEY goes here
└── demo.py                  # Automated demo script
```

## Environment Variables

```bash
GROQ_API_KEY=gsk_...          # Optional: enables Llama 3.3 70B responses
```

Without Groq key, the system uses fallback responses from indexed content.

## Demo

```bash
uvicorn app.main:app --reload
python demo.py
```

## Model Files

For P&ID digitization, download `32classes.pt` and place in `models/`:

```bash
# Download from DPID AI repository or your trained model
# Place at: models/32classes.pt
```
