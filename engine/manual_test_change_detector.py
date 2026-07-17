import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.change_detector import detect_changed_functions


def main():
    print("--- RippleGuard Manual Test (Change Detector) ---\n")

    # Two hardcoded versions of a small JS snippet.
    # DO NOT use fixture_repo files — these are self-contained test data.

    old_content = """\
function foo() {
  return 1;
}

function bar() {
  return 2;
}
"""

    new_content = """\
function foo() {
  return 99;
}

function bar() {
  return 2;
}

function baz() {
  console.log("I am new");
}
"""

    print("Old content:")
    print(old_content)
    print("New content:")
    print(new_content)

    try:
        changed = detect_changed_functions("test.js", old_content, new_content)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"Changed/added functions: {changed}")

    # Verify expected results
    expected = {"foo", "baz"}
    actual = set(changed)
    if actual == expected:
        print(f"\nPASS — matches expected: {expected}")
    else:
        print(f"\nFAIL — expected {expected}, got {actual}")


if __name__ == "__main__":
    main()
