import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.database import init_db, get_db
from app.models import DigitizationJob
from app.api.ingest import router as ingest_router
from app.api.knowledge import router as knowledge_router
from app.api.search import router as search_router
from app.api.query import router as query_router
from app.api.maintenance import router as maintenance_router
from app.api.compliance import router as compliance_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Industrial Knowledge Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(knowledge_router)
app.include_router(search_router)
app.include_router(query_router)
app.include_router(maintenance_router)
app.include_router(compliance_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/system")
def system_health():
    from app.services.integration import HealthChecker
    checker = HealthChecker(storage_dir="storage")
    return checker.check_all()


@app.post("/api/digitize")
async def digitize_pid(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())

    job = DigitizationJob(filename=file.filename, status="processing")
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        from app.services.pid_digitizer import PIDDigitizer
        digitizer = PIDDigitizer(storage_dir="storage", model_path="models/32classes.pt")
        result = digitizer.digitize(path)

        job.status = "completed"
        job.result_json = result
        db.commit()

        return JSONResponse({
            "job_id": job.id,
            "filename": file.filename,
            "status": "completed",
            "symbols_count": len(result.get("symbols", [])),
            "lines_count": len(result.get("lines", [])),
            "connections_count": len(result.get("connections", [])),
            "result": result,
        })
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        db.commit()
        raise HTTPException(500, f"Digitization failed: {str(e)}")


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return HTMLResponse(content=open(frontend_path).read())
    return HTMLResponse(content="<h1>Industrial Knowledge Assistant</h1><p>Frontend not found. API is running at /docs</p>")


@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dashboard.html")
    if os.path.exists(dashboard_path):
        return HTMLResponse(content=open(dashboard_path).read())
    return HTMLResponse(content="<h1>Dashboard not found</h1>")
