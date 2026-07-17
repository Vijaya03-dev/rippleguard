import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.function_graph_builder import build_function_graph


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    fixture_dir = os.path.join(project_root, 'fixture_repo')

    print("--- RippleGuard Manual Test (Function-Level Call Graph) ---")
    print(f"Scanning repo: {fixture_dir}\n")

    try:
        graph = build_function_graph(fixture_dir)
    except Exception as e:
        print(f"ERROR: Failed to build function graph: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"Total function nodes: {graph.number_of_nodes()}")
    print(f"Total call edges:     {graph.number_of_edges()}\n")

    # Print all nodes (functions discovered)
    print("Functions discovered:")
    for node in sorted(graph.nodes()):
        # Show just the basename::func for readability
        parts = node.rsplit("::", 1)
        display = f"  {os.path.basename(parts[0])}::{parts[1]}" if len(parts) == 2 else f"  {node}"
        print(display)
    print()

    # Print all edges (call relationships), sorted for consistent output
    print("Call edges:")
    edges = []
    for src, dst in graph.edges():
        src_parts = src.rsplit("::", 1)
        dst_parts = dst.rsplit("::", 1)
        src_display = f"{os.path.basename(src_parts[0])}::{src_parts[1]}" if len(src_parts) == 2 else src
        dst_display = f"{os.path.basename(dst_parts[0])}::{dst_parts[1]}" if len(dst_parts) == 2 else dst
        edges.append((src_display, dst_display))

    for src, dst in sorted(edges):
        print(f"  {src} -> {dst}")


if __name__ == "__main__":
    main()
