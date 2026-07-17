import os
from engine.change_detector import detect_changed_functions
from engine.function_graph_builder import build_function_graph


def analyze_function_change(
    repo_path: str,
    filepath: str,
    old_content: str,
    new_content: str
) -> dict:
    """
    Orchestrates function-level impact analysis:
    1. Detects which functions changed in `filepath` between `old_content` and `new_content`.
    2. Builds the repository-wide function call graph.
    3. Traverses call graph predecessors up to 2 levels to identify direct and indirect callers.

    Args:
        repo_path: Absolute path to the repository root.
        filepath: Absolute or relative path to the changed file.
        old_content: Original file content string.
        new_content: Modified file content string.

    Returns:
        A dictionary summarizing changed functions and affected caller functions.
    """
    filepath_norm = os.path.normpath(os.path.abspath(filepath))
    repo_path_norm = os.path.normpath(os.path.abspath(repo_path))

    # Step 1: Detect changed/added functions in the file
    changed_functions = detect_changed_functions(filepath_norm, old_content, new_content)

    # Step 2: Build the full function-level call graph
    graph = build_function_graph(repo_path_norm)

    affected_map: dict[str, dict] = {}

    # Step 3: For each changed function, traverse graph predecessors (callers)
    for func_name in changed_functions:
        # Find matching graph node: "filepath::function_name"
        target_node = None
        for node in graph.nodes():
            if "::" in node:
                f_path, f_name = node.rsplit("::", 1)
                if f_name == func_name and os.path.normpath(os.path.abspath(f_path)) == filepath_norm:
                    target_node = node
                    break

        if target_node is None or target_node not in graph:
            continue

        # Step 4: Direct callers (predecessors in directed call graph: A -> B means A calls B)
        try:
            direct_callers = list(graph.predecessors(target_node))
        except Exception as e:
            print(f"Warning: Error fetching predecessors for {target_node}: {e}")
            direct_callers = []

        for direct_node in direct_callers:
            if direct_node == target_node:
                continue

            d_path, d_name = direct_node.rsplit("::", 1)
            affected_map[direct_node] = {
                "function_name": d_name,
                "file": d_path,
                "severity": 1.0,
                "relationship": "direct_caller"
            }

            # Step 5: Indirect callers (callers of direct callers, 2 levels deep)
            try:
                indirect_callers = list(graph.predecessors(direct_node))
            except Exception as e:
                print(f"Warning: Error fetching predecessors for {direct_node}: {e}")
                indirect_callers = []

            for indirect_node in indirect_callers:
                if indirect_node == target_node:
                    continue
                # Only register indirect caller if not already registered as a direct caller
                if indirect_node not in affected_map:
                    i_path, i_name = indirect_node.rsplit("::", 1)
                    affected_map[indirect_node] = {
                        "function_name": i_name,
                        "file": i_path,
                        "severity": 0.5,
                        "relationship": "indirect_caller"
                    }

    affected_functions = list(affected_map.values())
    # Sort affected functions by severity descending, then by function name for stability
    affected_functions.sort(key=lambda x: (-x["severity"], x["function_name"]))

    return {
        "changed_file": filepath,
        "changed_functions": changed_functions,
        "affected_functions": affected_functions
    }
