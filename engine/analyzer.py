import os
import networkx as nx
from engine.graph_builder import build_dependency_graph
from engine.cochange_miner import get_cochange_frequencies
from engine.scoring import compute_severity_score


from engine.groq_client import get_explanation


# Minimum severity score to include a file in the output.  Anything below
# this is near-zero noise — files with no graph connection AND no co-change
# history.  0.1 filters those out while keeping anything with at least a
# weak signal from either source.
_SEVERITY_THRESHOLD = 0.1


def _find_git_root(start_path: str) -> str:
    """Walk up from start_path to find the nearest directory containing .git.

    WHY: repo_path might be a subdirectory of the actual git repo (e.g.
    fixture_repo/ inside the RippleGuard project root). The graph builder
    only needs os.walk, so any directory works. But the co-change miner
    needs a valid git repository with a .git directory. We auto-detect the
    git root rather than forcing callers to pass two separate paths.

    Raises FileNotFoundError if no .git is found all the way up to the
    filesystem root — this is a real error, not something to swallow.
    """
    current = os.path.abspath(start_path)
    while True:
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(
                f"No .git directory found in or above: {start_path}"
            )
        current = parent


def analyze_change(repo_path: str, changed_file: str) -> dict:
    """
    Orchestrate all RippleGuard phases to answer: "If I change this file,
    what else might break?"

    Args:
        repo_path: Absolute path to the directory to scan for source files.
            This may be the git root itself, or a subdirectory within a git
            repo (the git root is auto-detected for co-change mining).
        changed_file: Absolute path to the file being changed (must match the
            format used by graph_builder.py, which stores absolute paths as
            graph nodes).

    Returns:
        A dict with the shape:
        {
            "changed_file": "<absolute path>",
            "affected_files": [
                {
                    "affected_file": "<absolute path>",
                    "severity_score": 0.xx,
                    "severity_reason_codes": [...],
                    "plain_english_explanation": null
                },
                ...
            ]
        }
        affected_files is sorted by severity_score descending.
    """
    # --- Step 1: Build the dependency graph (Phase 3) ---
    # graph_builder uses os.walk, so repo_path can be any directory.
    graph = build_dependency_graph(repo_path)

    # --- Step 2: Get co-change frequencies (Phase 4) ---
    # get_cochange_frequencies needs a valid git repo (.git directory).
    # repo_path might be a subdirectory (e.g. fixture_repo/), so we walk
    # up to find the actual git root.
    git_root = _find_git_root(repo_path)
    cochange_data, _skipped = get_cochange_frequencies(git_root)

    # --- PATH FORMAT BRIDGE ---
    # graph_builder.py stores absolute paths as node keys.
    # cochange_miner.py stores paths relative to the GIT ROOT (forward-slash
    # normalized).
    #
    # To look up a co-change count for two graph nodes, we must convert both
    # absolute paths to git-root-relative paths, normalize to forward slashes,
    # then sort them into a canonical tuple matching the co-change dict's key
    # format.
    #
    # Critical: we use os.path.relpath(node, git_root) — NOT repo_path — because
    # co-change keys are relative to the git root where .git lives, not relative
    # to the scan directory passed to graph_builder.
    def _abs_to_relative(abs_path: str) -> str:
        """Convert an absolute graph-node path to the git-root-relative format
        used by cochange_miner (forward-slash normalized)."""
        return os.path.relpath(abs_path, git_root).replace("\\", "/")

    def _lookup_cochange(file_a_abs: str, file_b_abs: str) -> int:
        """Look up co-change frequency for two absolute paths, handling the
        sorted-tuple key convention from Phase 4."""
        rel_a = _abs_to_relative(file_a_abs)
        rel_b = _abs_to_relative(file_b_abs)
        # Phase 4 stores pairs as alphabetically-sorted tuples.
        key = tuple(sorted((rel_a, rel_b)))
        return cochange_data.get(key, 0)

    # --- Step 3: Score every other file in the graph ---
    affected_files = []

    for node in graph.nodes():
        if node == changed_file:
            continue

        # 3a. Compute graph_distance — shortest path in EITHER direction.
        # The changed file may import this node, or this node may import the
        # changed file.  Both directions represent breakage risk:
        #   - If auth.js imports utils.js and utils.js changes → auth.js may break
        #   - If utils.js is imported BY auth.js, changes to auth.js could
        #     affect utils.js's consumers transitively
        # We take the minimum distance across both directions.
        graph_distance = 999  # default: no path found in either direction
        try:
            d1 = nx.shortest_path_length(graph, source=changed_file, target=node)
            graph_distance = min(graph_distance, d1)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        try:
            d2 = nx.shortest_path_length(graph, source=node, target=changed_file)
            graph_distance = min(graph_distance, d2)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        # 3b. Look up co-change frequency (bridging absolute → relative paths).
        cochange_freq = _lookup_cochange(changed_file, node)

        # 3c. Compute severity score (all math lives in scoring.py).
        score = compute_severity_score(graph_distance, cochange_freq)

        # 3d. Build reason codes.
        reason_codes = []
        if graph_distance == 1:
            reason_codes.append("direct_import")
        if cochange_freq >= 2:
            reason_codes.append("high_cochange_frequency")
        if not reason_codes and (graph_distance < 999 or cochange_freq > 0):
            # There's some connection, but it's not a strong direct signal.
            reason_codes.append("indirect_relationship")

        # Step 4: Filter out near-zero-score noise.
        if score < _SEVERITY_THRESHOLD:
            continue

        explanation = get_explanation(
            reason_codes=reason_codes,
            changed_name=os.path.basename(changed_file),
            affected_name=os.path.basename(node)
        )

        affected_files.append({
            "affected_file": node,
            "severity_score": score,
            "severity_reason_codes": reason_codes,
            "plain_english_explanation": explanation,
        })

    # Sort by severity_score descending so the most critical files appear first.
    affected_files.sort(key=lambda x: -x["severity_score"])

    return {
        "changed_file": changed_file,
        "affected_files": affected_files,
    }
