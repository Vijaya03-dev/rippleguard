import os
from typing import Any, List, Optional
from tree_sitter import Parser
from tree_sitter_languages import get_language
from .base import LanguageResolver

class JSTSResolver(LanguageResolver):
    def __init__(self):
        self._js_parser = None
        self._ts_parser = None

    def _init_parser(self, language_name: str) -> Parser:
        """Manual override to bypass the broken internal library code."""
        lang = get_language(language_name)
        parser = Parser()
        parser.set_language(lang)
        return parser

    def parse_file(self, filepath: str) -> Any:
        try:
            with open(filepath, 'rb') as f:
                content_bytes = f.read()
        except Exception as e:
            print(f"Error: Could not read file '{filepath}': {e}")
            return None

        ext = os.path.splitext(filepath)[1].lower()
        parser = None
        
        try:
            if ext in ('.ts', '.tsx'):
                if self._ts_parser is None:
                    self._ts_parser = self._init_parser('typescript')
                parser = self._ts_parser
            else:
                if self._js_parser is None:
                    self._js_parser = self._init_parser('javascript')
                parser = self._js_parser
        except Exception as e:
            print(f"Error initializing parser: {e}")
            return None

        try:
            return parser.parse(content_bytes)
        except Exception as e:
            print(f"Error: Tree-sitter failed to parse '{filepath}': {e}")
            return None

    def _walk(self, node: Any) -> List[Any]:
        nodes = []
        if node is None:
            return nodes
        stack = [node]
        while stack:
            curr = stack.pop()
            nodes.append(curr)
            for child in reversed(curr.children):
                stack.append(child)
        return nodes

    def extract_imports(self, ast: Any) -> List[str]:
        imports = []
        if ast is None:
            return imports

        nodes = self._walk(ast.root_node)
        for node in nodes:
            if node.type == 'import_statement':
                for child in node.children:
                    if child.type == 'string':
                        try:
                            raw_text = child.text.decode('utf-8')
                            imports.append(raw_text.strip('\'"'))
                        except Exception:
                            pass
        return imports

    def extract_function_calls(self, ast: Any) -> List[str]:
        calls = []
        if ast is None:
            return calls

        nodes = self._walk(ast.root_node)
        for node in nodes:
            if node.type == 'call_expression':
                callee = node.child_by_field_name('function')
                if callee is None and len(node.children) > 0:
                    callee = node.children[0]
                
                if callee is not None:
                    try:
                        name = callee.text.decode('utf-8')
                        calls.append(name)
                    except Exception:
                        pass
        return calls

    def resolve_import_to_filepath(self, import_string: str, current_filepath: str) -> Optional[str]:
        if not import_string.startswith('.'):
            return None

        try:
            current_dir = os.path.dirname(os.path.abspath(current_filepath))
            target_path = os.path.abspath(os.path.join(current_dir, import_string))

            if os.path.isfile(target_path):
                return target_path
            js_path = target_path + '.js'
            if os.path.isfile(js_path):
                return js_path
            ts_path = target_path + '.ts'
            if os.path.isfile(ts_path):
                return ts_path
        except Exception:
            pass
        return None

    def extract_function_definitions(self, ast: Any) -> List[dict]:
        """
        Extract all named function definitions from a JS/TS AST.

        Targets:
          - 'function_declaration': top-level or exported named functions
            (e.g. `function foo() {}` or `export function foo() {}`)
          - 'method_definition': named methods inside class bodies
            (e.g. `class Foo { bar() {} }`)

        Skips arrow functions and anonymous function expressions since they
        don't produce named definitions that other files can import/call by
        name — keeping scope manageable for this phase.
        """
        definitions: List[dict] = []
        if ast is None:
            return definitions

        nodes = self._walk(ast.root_node)
        for node in nodes:
            if node.type not in ('function_declaration', 'method_definition'):
                continue

            name_node = node.child_by_field_name('name')
            if name_node is None:
                continue

            try:
                func_name = name_node.text.decode('utf-8')
            except Exception as e:
                print(f"Warning: could not decode function name: {e}")
                continue

            # tree-sitter positions are 0-indexed (row, col).
            # Convert to 1-indexed lines to match conventional line numbers.
            definitions.append({
                "name": func_name,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            })

        return definitions