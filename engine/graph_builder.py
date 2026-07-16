import os
import networkx as nx
from engine.resolvers.js_ts_resolver import JSTSResolver

# WHY: This module orchestrates the repository scanning. It walks the directory, 
# uses our LanguageResolver to parse imports, and uses networkx to build a DiGraph (Directed Graph).
# Nodes are absolute file paths, and directed edges represent dependencies (File A -> depends on -> File B).
def build_dependency_graph(repo_path: str) -> nx.DiGraph:
    """
    Scans a repository and builds a directed graph of file dependencies.
    """
    graph = nx.DiGraph()
    resolver = JSTSResolver()

    # 1. Find all JS/TS files in the repo
    target_files = []
    for root, _, files in os.walk(repo_path):
        # Skip node_modules or hidden folders
        if 'node_modules' in root or '/.' in root or '\\.' in root:
            continue
        for file in files:
            if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                target_files.append(os.path.join(root, file))

    # 2. Add all files as nodes first (even if they have no dependencies)
    for filepath in target_files:
        graph.add_node(filepath)

    # 3. Parse each file and build the edges
    for filepath in target_files:
        ast = resolver.parse_file(filepath)
        if ast is None:
            continue
        
        # Extract raw import strings (e.g., './utils.js')
        raw_imports = resolver.extract_imports(ast)
        
        # Resolve them to absolute paths and create edges
        for imp in raw_imports:
            resolved_path = resolver.resolve_import_to_filepath(imp, filepath)
            if resolved_path and os.path.exists(resolved_path):
                # Add edge: filepath -> resolved_path (meaning filepath depends on resolved_path)
                graph.add_edge(filepath, resolved_path)

    return graph