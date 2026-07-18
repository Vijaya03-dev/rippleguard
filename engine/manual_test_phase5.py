import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
from engine.analyzer import analyze_change


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    fixture_dir = os.path.join(project_root, "fixture_repo")

    # graph_builder.py stores ABSOLUTE paths as graph nodes (e.g.
    # "D:\RippleGaurd\fixture_repo\utils.js"), so changed_file must also
    # be an absolute path to match node lookups in the graph.
    changed_file = os.path.join(fixture_dir, "utils.js")

    print("--- RippleGuard Manual Test (Phase 5: Analyzer + Scoring) ---")
    print(f"Repo path:    {fixture_dir}")
    print(f"Changed file: {changed_file}\n")

    try:
        result = analyze_change(fixture_dir, changed_file)
    except Exception as e:
        print(f"ERROR: Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
