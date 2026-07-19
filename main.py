import os
import argparse
from core.universal_engine import UniversalEngine
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="DPID AI: Universal P&ID Digitization Engine")
    parser.add_argument("image_path", help="Path to the P&ID diagram (PNG/JPG)")
    parser.add_argument("--output", default="output", help="Output directory for JSON and visualizations")
    args = parser.parse_args()
    
    model_path = os.getenv("PT_MODEL_PATH", "models/32class.pt")
    
    if not os.path.exists(args.image_path):
        print(f"[ERROR] Image not found: {args.image_path}")
        return
    
    engine = UniversalEngine(
        model_path=model_path,
        output_dir=args.output
    )
    
    try:
        result = engine.process(args.image_path)
        print(f"\n[DONE] Found {len(result.get('detections', []))} symbols, {len(result.get('edges', []))} connections.")
    except Exception as e:
        print(f"[CRITICAL ERROR] Engine failed during digitization: {e}")

if __name__ == "__main__":
    main()
