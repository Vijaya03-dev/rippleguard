import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.cochange_miner import get_cochange_frequencies


def main():
    # The fixture_repo lives inside the main RippleGuard repo and does NOT
    # have its own .git directory.  Co-change mining must therefore run
    # against the *parent* repo root so GitPython can access the commit log.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)

    print("--- RippleGuard Manual Test (Phase 4: Co-Change Mining) ---")
    print(f"Mining git history at: {project_root}\n")

    try:
        pair_counts, skipped_count = get_cochange_frequencies(project_root)
    except Exception as e:
        print(f"ERROR: Failed to mine co-change history: {e}")
        sys.exit(1)

    print(f"Commits skipped (exceeded max_files_per_commit threshold): {skipped_count}")

    if not pair_counts:
        print("No co-changed file pairs found.")
        return

    # Sort by count descending, then alphabetically by pair for ties.
    sorted_pairs = sorted(pair_counts.items(), key=lambda x: (-x[1], x[0]))

    print(f"Total unique co-changed pairs: {len(sorted_pairs)}\n")
    print(f"{'Count':>5}  {'File A':<45} {'File B'}")
    print("-" * 100)
    for (file_a, file_b), count in sorted_pairs:
        print(f"{count:>5}  {file_a:<45} {file_b}")


if __name__ == "__main__":
    main()
