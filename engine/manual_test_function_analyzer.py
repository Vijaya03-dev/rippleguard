import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.function_analyzer import analyze_function_change


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    fixture_dir = os.path.join(project_root, "fixture_repo")
    auth_js_path = os.path.join(fixture_dir, "auth.js")

    print("--- RippleGuard Manual Test (Function-Level Analyzer) ---")
    print(f"Repo path: {fixture_dir}")
    print(f"Target file: {auth_js_path}\n")

    # Read actual CURRENT content of auth.js
    try:
        with open(auth_js_path, "r", encoding="utf-8") as f:
            old_content = f.read()
    except Exception as e:
        print(f"ERROR: Could not read {auth_js_path}: {e}")
        sys.exit(1)

    # Modify createSession body in new_content
    new_content = old_content.replace(
        "return { sessionId, userId };",
        "return { sessionId, userId, createdAt: Date.now() };"
    )

    try:
        result = analyze_function_change(
            repo_path=fixture_dir,
            filepath=auth_js_path,
            old_content=old_content,
            new_content=new_content
        )
    except Exception as e:
        print(f"ERROR: Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
