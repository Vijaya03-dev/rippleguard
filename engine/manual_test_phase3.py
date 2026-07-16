import os
import sys

# Add the project root directory to the python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.graph_builder import build_dependency_graph

def main():
    # 1. Setup paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    fixture_dir = os.path.join(project_root, 'fixture_repo')
    
    # 2. Auto-populate the dummy files so we know they have content!
    os.makedirs(fixture_dir, exist_ok=True)
    with open(os.path.join(fixture_dir, 'utils.js'), 'w') as f:
        f.write("export function loginUser() { return true; }")
    
    with open(os.path.join(fixture_dir, 'payments.js'), 'w') as f:
        f.write("export function processPayment() { return true; }")
    
    with open(os.path.join(fixture_dir, 'auth.js'), 'w') as f:
        f.write("import { loginUser } from './utils.js';\nimport { processPayment } from './payments.js';")

    print("--- RippleGuard Manual Test (Phase 3: Graph Builder) ---")
    print(f"Scanning repo: {fixture_dir}\n")

    # 3. Build the graph
    graph = build_dependency_graph(fixture_dir)

    # 4. Print the results mathematically
    print(f"Total Files (Nodes) Found: {graph.number_of_nodes()}")
    print(f"Total Dependencies (Edges) Found: {graph.number_of_edges()}\n")

    print("Dependency Map:")
    for node in graph.nodes():
        dependencies = list(graph.successors(node))
        filename = os.path.basename(node)
        
        if dependencies:
            deps_names = [os.path.basename(d) for d in dependencies]
            print(f"  [>] {filename} depends on -> {deps_names}")
        else:
            print(f"  [ ] {filename} (no dependencies)")

if __name__ == "__main__":
    main()