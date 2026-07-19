"""
Demo Script - Run through the system capabilities
"""
import requests
import json
import sys
import time

API = "http://localhost:8000"


def check_server():
    try:
        r = requests.get(f"{API}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def demo_upload():
    print("\n[1] Upload a P&ID image")
    print("    POST /api/digitize")
    # Would need an actual file - skip for demo
    print("    (Skipped - requires image file)")


def demo_ingest():
    print("\n[2] Ingest a document")
    print("    POST /api/ingest")
    try:
        r = requests.post(f"{API}/api/ingest", json={
            "content": "Pump P-101 is a centrifugal pump rated at 500 GPM. "
                       "Operator must verify suction pressure before starting. "
                       "Emergency shutdown procedure: Close valve V-001.",
            "document_type": "maintenance_record",
            "metadata": {"equipment_tag": "P-101", "date": "2024-01-15"},
        })
        print(f"    Result: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"    Error: {e}")


def demo_search():
    print("\n[3] Search knowledge")
    print("    GET /api/search")
    try:
        r = requests.get(f"{API}/api/search", params={"q": "pump maintenance"})
        data = r.json()
        print(f"    Found {len(data.get('results', []))} results")
        for hit in data.get("results", [])[:3]:
            print(f"      - {hit.get('text', '')[:80]}...")
    except Exception as e:
        print(f"    Error: {e}")


def demo_query():
    print("\n[4] RAG Query")
    print("    GET /api/query")
    try:
        r = requests.get(f"{API}/api/query", params={"q": "What is the maintenance procedure for P-101?"})
        data = r.json()
        print(f"    Answer: {data.get('answer', 'N/A')[:200]}")
        print(f"    Sources: {data.get('sources', [])}")
    except Exception as e:
        print(f"    Error: {e}")


def demo_knowledge_graph():
    print("\n[5] Knowledge Graph")
    print("    GET /api/knowledge-graph")
    try:
        r = requests.get(f"{API}/api/knowledge-graph")
        data = r.json()
        print(f"    Nodes: {len(data.get('nodes', []))}")
        print(f"    Links: {len(data.get('links', []))}")
    except Exception as e:
        print(f"    Error: {e}")


def demo_equipment():
    print("\n[6] Equipment List")
    print("    GET /api/equipment")
    try:
        r = requests.get(f"{API}/api/equipment")
        data = r.json()
        print(f"    Found {len(data)} equipment items")
        for eq in data[:3]:
            print(f"      - {eq.get('tag', 'Unknown')}: {eq.get('equipment_type', 'N/A')}")
    except Exception as e:
        print(f"    Error: {e}")


def demo_maintenance():
    print("\n[7] Maintenance Intelligence")
    print("    GET /api/maintenance/schedule")
    try:
        r = requests.get(f"{API}/api/maintenance/schedule")
        data = r.json()
        print(f"    Tasks: {len(data)}")
    except Exception as e:
        print(f"    Error: {e}")


def demo_compliance():
    print("\n[8] Compliance Status")
    print("    GET /api/compliance/status")
    try:
        r = requests.get(f"{API}/api/compliance/status")
        data = r.json()
        print(f"    Status: {json.dumps(data, indent=2)[:300]}")
    except Exception as e:
        print(f"    Error: {e}")


def demo_health():
    print("\n[9] System Health")
    print("    GET /health/system")
    try:
        r = requests.get(f"{API}/health/system")
        data = r.json()
        print(f"    Status: {data.get('status')}")
        for name, check in data.get("checks", {}).items():
            print(f"      {name}: {check.get('status')}")
    except Exception as e:
        print(f"    Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("ET Hackathon 2.0 - Industrial Knowledge Assistant Demo")
    print("=" * 60)

    if not check_server():
        print("\nServer not running. Start with: uvicorn app.main:app --reload")
        sys.exit(1)

    print("\nServer is running!")

    demo_ingest()
    demo_search()
    demo_query()
    demo_knowledge_graph()
    demo_equipment()
    demo_maintenance()
    demo_compliance()
    demo_health()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
