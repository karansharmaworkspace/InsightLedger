"""Local network server — exposes full app via HTTP on 0.0.0.0."""
from __future__ import annotations

import json
import os
import sys
import time
import threading
import traceback
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, Response

# Ensure project root on path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

app = Flask(__name__, static_folder="web", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB upload


def _sanitize_json(obj):
    """Recursively convert numpy types to native Python for jsonify."""
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_json(v) for v in obj]
    if hasattr(obj, 'item'):
        return obj.item()
    return obj


@app.after_request
def add_no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ── Lazy singletons (thread-safe) ────────────────────────────────────
_platform = None
_engine = None
_kg = None
_rag = None
_okf_rag = None
_lock = threading.Lock()


def _get_platform():
    global _platform
    if _platform is None:
        with _lock:
            if _platform is None:
                from core.knowledge_platform import KnowledgePlatform
                _platform = KnowledgePlatform(base_dir=ROOT)
    return _platform


def _get_kg():
    global _kg
    if _kg is None:
        with _lock:
            if _kg is None:
                from core.knowledge_graph import KnowledgeGraph
                _kg = KnowledgeGraph(os.path.join(ROOT, "Storage", "graphs", "knowledge_graph.json"))
    return _kg


def _get_rag():
    global _rag
    if _rag is None:
        with _lock:
            if _rag is None:
                from core.embeddings_rag import EmbeddingsRAG
                _rag = EmbeddingsRAG(
                    storage_path=os.path.join(ROOT, "Storage", "graphs", "embeddings.json")
                ).load()
    return _rag


def _get_okf_rag():
    global _okf_rag
    if _okf_rag is None:
        with _lock:
            if _okf_rag is None:
                try:
                    from core.okf_rag import OKFRAGChat
                    _okf_rag = OKFRAGChat()
                except Exception as e:
                    print(f"[OKF-RAG] Init failed: {e}")
    return _okf_rag


def _get_engine():
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                from core.universal_engine import UniversalEngine
                _engine = UniversalEngine(
                    model_path=os.path.join(ROOT, "models", "32class.pt"),
                    output_dir=os.path.join(ROOT, "Storage", "outputs"),
                )
    return _engine


# ── Static ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("web", path)


# ── Knowledge Graph API ──────────────────────────────────────────────
@app.route("/api/kg/stats")
def kg_stats():
    kg = _get_kg()
    return jsonify(kg.get_stats())


@app.route("/api/kg/nodes")
def kg_nodes():
    kg = _get_kg()
    etype = request.args.get("type")
    source = request.args.get("source")
    if etype:
        nodes = kg.find_by_type(etype)
    elif source:
        nodes = kg.find_by_source(source)
    else:
        nodes = list(kg.nodes.values())
    # Limit response size
    limit = int(request.args.get("limit", 2000))
    return jsonify(nodes[:limit])


@app.route("/api/kg/edges")
def kg_edges():
    kg = _get_kg()
    return jsonify(kg.edges[:5000])


@app.route("/api/kg/search")
def kg_search():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])
    kg = _get_kg()
    results = []
    for nid, node in kg.nodes.items():
        if q in node.get("value", "").lower() or q in node.get("type", "").lower():
            results.append(node)
    return jsonify(results[:200])


@app.route("/api/kg/network")
def kg_network():
    value = request.args.get("value", "")
    depth = int(request.args.get("depth", 2))
    kg = _get_kg()
    return jsonify(kg.get_entity_network(value, depth))


@app.route("/api/kg/types")
def kg_types():
    kg = _get_kg()
    types = {}
    for node in kg.nodes.values():
        t = node["type"]
        types[t] = types.get(t, 0) + 1
    return jsonify(types)


@app.route("/api/kg/sources")
def kg_sources():
    kg = _get_kg()
    sources = {}
    for node in kg.nodes.values():
        for s in node.get("sources", []):
            sources[s] = sources.get(s, 0) + 1
    return jsonify(sources)


# ── Embeddings RAG search ────────────────────────────────────────────
@app.route("/api/search")
def semantic_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    rag = _get_rag()
    results = rag.search(q, top_k=int(request.args.get("top_k", 10)))
    return jsonify(results)


# ── OKF API ──────────────────────────────────────────────────────────
@app.route("/api/okf/classes")
def okf_classes():
    okf_dir = os.path.join(ROOT, "okf", "classes")
    if not os.path.isdir(okf_dir):
        return jsonify([])
    import yaml
    classes = []
    for fname in sorted(os.listdir(okf_dir)):
        if not fname.endswith(".md"):
            continue
        text = open(os.path.join(okf_dir, fname), "r", encoding="utf-8").read()
        meta = {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1]) or {}
                except Exception:
                    pass
        subs = []
        in_list = False
        for line in text.split("\n"):
            if line.strip() == "## Subclasses":
                in_list = True
                continue
            if in_list and line.startswith("- "):
                subs.append(line[2:].strip())
            elif in_list and line.startswith("#"):
                break
        classes.append({"file": fname, "meta": meta, "subclasses": subs, "count": len(subs)})
    return jsonify(classes)


@app.route("/api/okf/search")
def okf_search():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])
    rag = _get_okf_rag()
    if rag is None:
        return jsonify({"error": "OKF-RAG not available"}), 503
    results = rag.search(q, top_k=int(request.args.get("top_k", 10)))
    return jsonify(results)


@app.route("/api/okf/chat", methods=["POST"])
def okf_chat():
    data = request.get_json() or {}
    q = data.get("message", "").strip()
    if not q:
        return jsonify({"error": "No message"}), 400
    rag = _get_okf_rag()
    if rag is None:
        return jsonify({"error": "OKF-RAG not available"}), 503
    try:
        response = rag.ask(q, stream=False)
        if response and hasattr(response, 'choices'):
            answer = response.choices[0].message.content
        else:
            answer = "No response from model"
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Document ingestion API ───────────────────────────────────────────
@app.route("/api/documents/ingest", methods=["POST"])
def ingest_document():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    upload_dir = os.path.join(ROOT, "Storage", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, f.filename)
    f.save(save_path)

    platform = _get_platform()
    result = platform.ingest_document(save_path)
    return jsonify(result)


@app.route("/api/documents")
def list_documents():
    doc_dir = os.path.join(ROOT, "Storage", "documents")
    uploads_dir = os.path.join(ROOT, "Storage", "uploads")
    docs = []
    for d in [doc_dir, uploads_dir]:
        if os.path.isdir(d):
            for fname in os.listdir(d):
                fpath = os.path.join(d, fname)
                if os.path.isfile(fpath):
                    docs.append({
                        "name": fname,
                        "size": os.path.getsize(fpath),
                        "path": fpath,
                    })
    return jsonify(docs)


@app.route("/api/documents/search")
def search_documents():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    rag = _get_rag()
    results = rag.search(q, top_k=int(request.args.get("top_k", 10)))
    return jsonify(results)


# ── P&ID processing API ──────────────────────────────────────────────
@app.route("/api/process/pid", methods=["POST"])
def process_pid():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    upload_dir = os.path.join(ROOT, "Storage", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, f.filename)
    f.save(save_path)

    try:
        engine = _get_engine()
        results = engine.process(save_path)
        _last_pid_results.update(results)
        return jsonify(_sanitize_json(results))
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/process/status")
def process_status():
    return jsonify({"status": "ready"})


# ── Reclassification API ─────────────────────────────────────────────
# ponytail: in-memory store for last processing results, good enough for hackathon
_last_pid_results = {}


@app.route("/api/process/reclassify", methods=["POST"])
def reclassify_symbol():
    data = request.get_json() or {}
    node_id = data.get("node_id")
    new_class = data.get("new_class")
    parent_class = data.get("parent_class", "")
    if not node_id or not new_class:
        return jsonify({"error": "node_id and new_class required"}), 400

    engine = _get_engine()
    nodes = _last_pid_results.get("nodes", [])
    if not nodes:
        return jsonify({"error": "No processing results available"}), 400

    ok = engine.reclassify_symbol(node_id, new_class, parent_class, nodes)
    if ok:
        return jsonify({"status": "ok", "node_id": node_id, "new_class": new_class})
    return jsonify({"error": f"Node {node_id} not found"}), 404


@app.route("/api/process/classes")
def symbol_classes():
    """Return the full classification hierarchy for the dropdown."""
    engine = _get_engine()
    if hasattr(engine, "class_memory") and hasattr(engine.class_memory, "get_hierarchy"):
        return jsonify(engine.class_memory.get_hierarchy())
    # Fallback: return flat list from OKF classes
    okf_dir = os.path.join(ROOT, "okf", "classes")
    if not os.path.isdir(okf_dir):
        return jsonify([])
    import yaml
    classes = []
    for fname in sorted(os.listdir(okf_dir)):
        if not fname.endswith(".md"):
            continue
        text = open(os.path.join(okf_dir, fname), "r", encoding="utf-8").read()
        match = re.search(r'^name:\s*"?(.+?)"?\s*$', text, re.MULTILINE)
        if match:
            classes.append(match.group(1))
    return jsonify(classes)


# ── Entity extraction API ────────────────────────────────────────────
@app.route("/api/entities/extract", methods=["POST"])
def extract_entities():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify([])
    from core.entity_extractor import EntityExtractor
    ext = EntityExtractor()
    entities = ext.extract(text)
    return jsonify([{
        "type": e.entity_type,
        "value": e.value,
        "confidence": e.confidence,
    } for e in entities])


# ── Maintenance & Compliance ─────────────────────────────────────────
@app.route("/api/maintenance/schedule")
def maintenance_schedule():
    platform = _get_platform()
    schedule = platform.maintenance.get_upcoming_schedule()
    return jsonify(schedule)


@app.route("/api/compliance/gaps")
def compliance_gaps():
    platform = _get_platform()
    text = request.args.get("text", "")
    doc_type = request.args.get("doc_type", "procedure")
    gaps = platform.compliance.find_gaps(text, doc_type)
    return jsonify(gaps)


@app.route("/api/compliance/audit")
def compliance_audit():
    platform = _get_platform()
    audit = platform.compliance.generate_audit_trail()
    return jsonify(audit)


# ── Health ───────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "modules": {
            "knowledge_graph": _kg is not None,
            "embeddings_rag": _rag is not None,
            "okf_rag": _okf_rag is not None,
            "engine": _engine is not None,
        },
    })


# ── Storage Browser ─────────────────────────────────────────────────
@app.route("/api/storage")
@app.route("/api/storage/<path:subpath>")
def storage_browser(subpath=""):
    base = os.path.join(ROOT, "Storage")
    target = os.path.join(base, subpath)
    if not os.path.abspath(target).startswith(os.path.abspath(base)):
        return jsonify({"error": "Access denied"}), 403
    if not os.path.exists(target):
        return jsonify({"error": "Path not found"}), 404
    if os.path.isfile(target):
        return send_from_directory(os.path.dirname(target), os.path.basename(target))
    items = []
    for name in sorted(os.listdir(target)):
        full = os.path.join(target, name)
        items.append({
            "name": name,
            "type": "dir" if os.path.isdir(full) else "file",
            "size": os.path.getsize(full) if os.path.isfile(full) else 0,
            "path": os.path.relpath(full, base).replace("\\", "/"),
        })
    return jsonify({"path": subpath or "/", "items": items})


@app.route("/api/storage/download/<path:filepath>")
def storage_download(filepath):
    base = os.path.join(ROOT, "Storage")
    target = os.path.join(base, filepath)
    if not os.path.abspath(target).startswith(os.path.abspath(base)):
        return jsonify({"error": "Access denied"}), 403
    if not os.path.isfile(target):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(os.path.dirname(target), os.path.basename(target), as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  DOCOKF — Local Server")
    print(f"  http://0.0.0.0:{port}")
    print(f"  Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=port, debug=True)
