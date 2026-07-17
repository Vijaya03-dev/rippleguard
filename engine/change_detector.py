from tree_sitter import Parser
from tree_sitter_languages import get_language
from engine.resolvers.js_ts_resolver import JSTSResolver


def detect_changed_functions(
    filepath: str, old_content: str, new_content: str
) -> list[str]:
    """
    Given a file path and two versions of its content (old and new), return
    the names of functions whose bodies changed or that were newly added.

    Args:
        filepath: Used only to determine the language (JS vs TS) via the
            file extension.  The file is NOT read from disk — both content
            strings are passed in directly so this function stays pure and
            testable without touching the filesystem.
        old_content: The file's content before the change.
        new_content: The file's content after the change.

    Returns:
        A list of function name strings that were either modified or newly
        added in new_content compared to old_content.

    WHY comparing function body TEXT rather than full AST diffing:
        Full semantic AST diffing (detecting structurally equivalent but
        differently-formatted code, reordered statements, etc.) is a
        substantially harder problem that would require a tree-diff
        algorithm like GumTree or similar.  Comparing the exact source
        text of each function's line range is a simple, honest, good-enough
        heuristic for this scope: if the developer edited anything inside
        the function — even whitespace or a comment — it shows up as a
        change.  This over-reports slightly (formatting-only changes) but
        never under-reports (a real logic change is always caught), which
        is the safer direction for a risk-detection tool.
    """
    # --- Parse both versions into ASTs ---
    parser = _get_parser(filepath)
    old_ast = _parse_content(parser, old_content)
    new_ast = _parse_content(parser, new_content)

    # --- Extract function definitions from both ---
    resolver = JSTSResolver()
    old_defs = resolver.extract_function_definitions(old_ast)
    new_defs = resolver.extract_function_definitions(new_ast)

    # Build lookup maps: function_name -> definition dict
    old_by_name = {d["name"]: d for d in old_defs}
    new_by_name = {d["name"]: d for d in new_defs}

    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    changed: list[str] = []

    for func_name, new_def in new_by_name.items():
        if func_name not in old_by_name:
            # Newly added function — counts as a change worth flagging.
            changed.append(func_name)
            continue

        # Function exists in both versions — compare the actual source text
        # of its body by slicing the content lines using start_line/end_line.
        old_def = old_by_name[func_name]
        old_body = _extract_body_text(old_lines, old_def)
        new_body = _extract_body_text(new_lines, new_def)

        if old_body != new_body:
            changed.append(func_name)

    # Deletions (in old but not in new) are deliberately skipped for now —
    # they're a separate future case to avoid overcomplicating this chunk.

    return changed


# ─── Internal helpers ────────────────────────────────────────────────────

def _get_parser(filepath: str) -> Parser:
    """
    Create a tree-sitter Parser for the language indicated by filepath's
    extension.

    WHY not reuse JSTSResolver's internal parser:
        The resolver's parser is a private implementation detail (_js_parser,
        _ts_parser) behind its parse_file() method, which reads from disk.
        We need to parse raw string content without touching the filesystem.
        Creating our own Parser here (same 3-line init the resolver uses)
        keeps this module standalone and avoids reaching into private
        internals of a class we're told not to modify.
    """
    import os
    ext = os.path.splitext(filepath)[1].lower()
    lang_name = 'typescript' if ext in ('.ts', '.tsx') else 'javascript'
    lang = get_language(lang_name)
    parser = Parser()
    parser.set_language(lang)
    return parser


def _parse_content(parser: Parser, content: str) -> object:
    """Parse a raw content string into a tree-sitter AST."""
    return parser.parse(content.encode('utf-8'))


def _extract_body_text(lines: list[str], func_def: dict) -> str:
    """
    Slice the source lines to extract the full text of a function body.
    start_line and end_line are 1-indexed (from extract_function_definitions).
    """
    start = func_def["start_line"] - 1  # convert to 0-indexed
    end = func_def["end_line"]          # end_line is inclusive, slice is exclusive
    return "\n".join(lines[start:end])
