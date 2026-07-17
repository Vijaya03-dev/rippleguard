import os
import networkx as nx
from engine.resolvers.js_ts_resolver import JSTSResolver


def build_function_graph(repo_path: str) -> nx.DiGraph:
    """
    Build a directed graph where nodes are "filepath::function_name" and edges
    represent function-level call relationships (callerFile::callerFunc ->
    calleeFile::calleeFunc).

    Uses absolute file paths in node keys to match the file-level graph
    produced by graph_builder.py (which also uses absolute paths), ensuring
    both graphs are compatible for later merge/analysis.

    Returns:
        A networkx DiGraph with "filepath::function_name" string nodes.
    """
    graph = nx.DiGraph()
    resolver = JSTSResolver()

    # --- 1. Discover all JS/TS files ---
    target_files: list[str] = []
    for root, _, files in os.walk(repo_path):
        if 'node_modules' in root or '/.' in root or '\\.' in root:
            continue
        for file in files:
            if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                target_files.append(os.path.join(root, file))

    # --- 2. Parse every file and collect function definitions ---
    # file_defs maps absolute_filepath -> list of definition dicts
    # (each dict has "name", "start_line", "end_line")
    file_defs: dict[str, list[dict]] = {}
    # file_asts caches the parsed AST so we don't re-parse in step 3
    file_asts: dict[str, object] = {}

    for filepath in target_files:
        ast = resolver.parse_file(filepath)
        if ast is None:
            continue
        file_asts[filepath] = ast
        defs = resolver.extract_function_definitions(ast)
        file_defs[filepath] = defs

        # Add every function as a graph node, even if it has no edges.
        for d in defs:
            graph.add_node(f"{filepath}::{d['name']}")

    # --- 3. For each file, resolve function calls to their targets ---
    for filepath in target_files:
        ast = file_asts.get(filepath)
        if ast is None:
            continue

        defs_in_file = file_defs.get(filepath, [])

        # Resolve this file's imports to absolute paths.
        raw_imports = resolver.extract_imports(ast)
        imported_filepaths: list[str] = []
        for imp in raw_imports:
            resolved = resolver.resolve_import_to_filepath(imp, filepath)
            if resolved and os.path.exists(resolved):
                imported_filepaths.append(resolved)

        # Get function calls WITH their line positions.
        # We walk the AST manually here because the existing
        # extract_function_calls method returns only names (no positions),
        # and we must not modify it.  We need the line number of each call
        # so we can determine which enclosing function contains it.
        positioned_calls = _extract_positioned_calls(ast, resolver)

        for call_name, call_line in positioned_calls:
            # Determine which function in THIS file contains this call.
            caller_func = _find_enclosing_function(call_line, defs_in_file)
            if caller_func is None:
                # Call is at module/top level, outside any function body.
                # Skip — we only track function-to-function edges.
                continue

            # Resolve the call target: which file and function is being called?
            target = _resolve_call_target(
                call_name, filepath, defs_in_file,
                imported_filepaths, file_defs
            )
            if target is None:
                # Could not resolve — likely a built-in (Math.random,
                # console.log) or a method chain (amount.toFixed).
                # Silently skip rather than guess or crash.
                continue

            target_filepath, target_func_name = target
            caller_node = f"{filepath}::{caller_func}"
            callee_node = f"{target_filepath}::{target_func_name}"

            graph.add_edge(caller_node, callee_node)

    return graph


# ─── Helper functions ────────────────────────────────────────────────────

def _extract_positioned_calls(ast: object, resolver: JSTSResolver) -> list[tuple[str, int]]:
    """
    Walk the AST and return (call_name, 1-indexed_line) for every
    call_expression node.
    """
    calls: list[tuple[str, int]] = []
    nodes = resolver._walk(ast.root_node)  # type: ignore[attr-defined]
    for node in nodes:
        if node.type != 'call_expression':
            continue
        callee = node.child_by_field_name('function')
        if callee is None and len(node.children) > 0:
            callee = node.children[0]
        if callee is not None:
            try:
                name = callee.text.decode('utf-8')
                # tree-sitter start_point is (row, col), 0-indexed
                line = node.start_point[0] + 1
                calls.append((name, line))
            except Exception as e:
                print(f"Warning: could not decode call expression: {e}")
    return calls


def _find_enclosing_function(call_line: int, defs: list[dict]) -> str | None:
    """
    Given a call's 1-indexed line number and the list of function
    definitions in the same file, return the name of the innermost
    function that contains that line, or None if the call is at the
    top level (outside all functions).
    """
    best_match: dict | None = None
    for d in defs:
        if d['start_line'] <= call_line <= d['end_line']:
            # If multiple functions contain this line (shouldn't happen
            # for non-nested functions, but be safe), pick the narrowest.
            if best_match is None or (d['end_line'] - d['start_line']) < (best_match['end_line'] - best_match['start_line']):
                best_match = d
    return best_match['name'] if best_match else None


def _resolve_call_target(
    call_name: str,
    current_filepath: str,
    current_file_defs: list[dict],
    imported_filepaths: list[str],
    all_file_defs: dict[str, list[dict]],
) -> tuple[str, str] | None:
    """
    Given a raw call name (e.g. "generateId"), resolve it to
    (defining_filepath, function_name) or None if unresolvable.

    WHY same-file-first, then imported-file lookup:
        JavaScript/TypeScript scoping rules mean a local definition
        shadows any imported name with the same identifier. If a file
        defines its own `foo` AND imports a `foo` from another module,
        a bare call to `foo()` inside that file refers to the local
        definition. Checking the current file first mirrors this
        scoping behavior and avoids false-positive matches where we'd
        incorrectly attribute the call to an unrelated function in
        another file that happens to share the same name.

    We only attempt resolution for simple identifiers (no dots).
    Dotted names like "Math.random" or "amount.toFixed" are method
    calls or property accesses on objects — resolving those would
    require type inference, which is out of scope.
    """
    # Skip dotted names (method calls, property access chains).
    # These are things like "Math.random", "console.log", "amount.toFixed"
    # which can't be resolved by simple name matching.
    if '.' in call_name:
        return None

    # 1. Check the current file's own definitions first (same-file call).
    for d in current_file_defs:
        if d['name'] == call_name:
            return (current_filepath, call_name)

    # 2. Check each imported file's definitions.
    for imp_filepath in imported_filepaths:
        imp_defs = all_file_defs.get(imp_filepath, [])
        for d in imp_defs:
            if d['name'] == call_name:
                return (imp_filepath, call_name)

    # 3. Not found anywhere — likely a built-in, global, or something
    #    we don't handle yet. Return None (caller will skip silently).
    return None
