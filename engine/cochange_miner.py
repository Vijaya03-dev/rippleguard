from itertools import combinations
from git import Repo, NULL_TREE


def get_cochange_frequencies(repo_path: str, max_files_per_commit: int = 15) -> tuple[dict[tuple[str, str], int], int]:
    """
    Walk every commit in a repo's history and count how often each pair of files
    was changed together in the same commit.

    Args:
        repo_path: Path to the git repository root.
        max_files_per_commit: Commits touching MORE than this many files are
            skipped entirely.

            WHY: Large commits usually represent bulk/unrelated changes — initial
            project scaffolding, dependency lockfile updates, automated code
            generation, or mass renames — rather than genuine functional coupling
            between files. Including them floods the output with spurious pairs
            (e.g. C(37,2) = 666 pairs from one scaffolding commit) that drown
            out real signal. Excluding oversized commits is standard practice in
            co-change analysis, not an arbitrary cut.

    Returns:
        A tuple of (pair_counts, skipped_count) where:
          - pair_counts: dict mapping (file_a, file_b) -> int co-change count.
            Keys are repo-relative paths (forward-slash normalized). The tuple
            is always sorted alphabetically so ('a.js', 'b.js') and
            ('b.js', 'a.js') are never stored as separate keys.
          - skipped_count: how many commits were excluded by the threshold.

    WHY sorted-tuple keys:
        Without canonicalization, the pair (X, Y) could be recorded as both
        (X, Y) and (Y, X) depending on iteration order, inflating counts and
        making lookups unreliable. Sorting guarantees exactly one canonical key
        per unordered pair.

    WHY relative paths:
        The dependency graph built in Phase 3 currently uses absolute paths as
        node keys. However, co-change data must be portable across machines and
        comparable across analysis runs. Relative paths are the natural key for
        git history (git itself stores paths relative to the repo root). When
        Phase 5+ merges these two data sources, we can normalize the graph's
        absolute paths to relative at the join point — that's a one-line
        conversion. Storing absolute paths here would bake in machine-specific
        prefixes that silently break lookups on any other machine or CI runner.
    """
    repo = Repo(repo_path)
    pair_counts: dict[tuple[str, str], int] = {}
    skipped_count = 0

    for commit in repo.iter_commits("--all"):
        # Get the list of files changed in this commit.
        # For the very first commit (no parents), diff against the empty tree
        # so we still capture which files were introduced.
        if commit.parents:
            # Diff against the first parent (standard for non-merge commits).
            diffs = commit.diff(commit.parents[0])
        else:
            # Root commit: diff against NULL_TREE (GitPython's sentinel for
            # "empty tree") to see every file the commit introduced.
            diffs = commit.diff(NULL_TREE)

        # Collect unique relative file paths touched by this commit.
        # Each diff item has an a_path (old name) and b_path (new name);
        # for renames both matter, for normal edits they're the same.
        # We normalize to forward slashes for cross-platform consistency.
        changed_files: set[str] = set()
        for diff_item in diffs:
            if diff_item.a_path:
                changed_files.add(diff_item.a_path.replace("\\", "/"))
            if diff_item.b_path:
                changed_files.add(diff_item.b_path.replace("\\", "/"))

        # Skip commits that touched too many files — they represent bulk
        # changes (scaffolding, lockfiles) not genuine functional coupling.
        if len(changed_files) > max_files_per_commit:
            skipped_count += 1
            continue

        # For every unique pair of co-changed files, increment the counter.
        # combinations() on a sorted list produces alphabetically-sorted pairs,
        # giving us our canonical key without an extra sort step per pair.
        for file_a, file_b in combinations(sorted(changed_files), 2):
            pair = (file_a, file_b)
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    return pair_counts, skipped_count
