import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.graph_builder import build_dependency_graph
from engine.function_graph_builder import build_function_graph


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    fixture_dir = os.path.join(project_root, 'fixture_repo_python')

    print("--- RippleGuard Manual Test (Python Fixture Graph Analysis) ---")
    print(f"Scanning repo: {fixture_dir}\n")

    # 1. File-level Dependency Graph (matching manual_test_phase3.py format)
    print("=== File-Level Dependency Graph ===")
    dep_graph = build_dependency_graph(fixture_dir)
    print(f"Total Files (Nodes) Found: {dep_graph.number_of_nodes()}")
    print(f"Total Dependencies (Edges) Found: {dep_graph.number_of_edges()}\n")

    print("Dependency Map:")
    for node in sorted(dep_graph.nodes()):
        dependencies = list(dep_graph.successors(node))
        filename = os.path.basename(node)
        if dependencies:
            deps_names = [os.path.basename(d) for d in dependencies]
            print(f"  [>] {filename} depends on -> {deps_names}")
        else:
            print(f"  [ ] {filename} (no dependencies)")
    print()

    # 2. Function-Level Call Graph (matching manual_test_function_graph.py format)
    print("=== Function-Level Call Graph ===")
    func_graph = build_function_graph(fixture_dir)

    print(f"Total function nodes: {func_graph.number_of_nodes()}")
    print(f"Total call edges:     {func_graph.number_of_edges()}\n")

    print("Functions discovered:")
    for node in sorted(func_graph.nodes()):
        parts = node.rsplit("::", 1)
        display = f"  {os.path.basename(parts[0])}::{parts[1]}" if len(parts) == 2 else f"  {node}"
        print(display)
    print()

    print("Call edges:")
    edges = []
    for src, dst in func_graph.edges():
        src_parts = src.rsplit("::", 1)
        dst_parts = dst.rsplit("::", 1)
        src_display = f"{os.path.basename(src_parts[0])}::{src_parts[1]}" if len(src_parts) == 2 else src
        dst_display = f"{os.path.basename(dst_parts[0])}::{dst_parts[1]}" if len(dst_parts) == 2 else dst
        edges.append((src_display, dst_display))

    for src, dst in sorted(edges):
        print(f"  {src} -> {dst}")


if __name__ == "__main__":
    main()
