import os
import ast
from typing import Any, List, Optional
from .base import LanguageResolver

class PythonResolver(LanguageResolver):
    def parse_file(self, filepath: str) -> Any:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return ast.parse(content, filename=filepath)
        except (UnicodeDecodeError, OSError, SyntaxError) as e:
            print(f"Error parsing file '{filepath}': {e}")
            return None

    def parse_content(self, content: str) -> Any:
        """Helper method to parse string content directly (e.g. for the change detector)."""
        try:
            return ast.parse(content)
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing content: {e}")
            return None

    def extract_imports(self, ast_tree: Any) -> List[str]:
        imports = []
        if ast_tree is None:
            return imports

        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Import):
                for name_alias in node.names:
                    imports.append(name_alias.name)
            elif isinstance(node, ast.ImportFrom):
                level = node.level or 0
                if level > 0:
                    dots = '.' * level
                    if node.module:
                        imports.append(dots + node.module)
                    else:
                        for name_alias in node.names:
                            imports.append(dots + name_alias.name)
                else:
                    if node.module:
                        imports.append(node.module)

        # Return unique imports preserving order
        return list(dict.fromkeys(imports))

    def _get_call_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._get_call_name(node.value)
            if val:
                return f"{val}.{node.attr}"
        return None

    def extract_function_calls(self, ast_tree: Any) -> List[str]:
        calls = []
        if ast_tree is None:
            return calls

        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Call):
                name = self._get_call_name(node.func)
                if name:
                    calls.append(name)
        return calls

    def extract_function_definitions(self, ast_tree: Any) -> List[dict]:
        definitions = []
        if ast_tree is None:
            return definitions

        for node in ast.walk(ast_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = getattr(node, 'lineno', 1)
                end = getattr(node, 'end_lineno', start)
                definitions.append({
                    "name": node.name,
                    "start_line": start,
                    "end_line": end
                })
        return definitions

    def resolve_import_to_filepath(self, import_string: str, current_filepath: str) -> Optional[str]:
        # Count leading dots
        dots_count = 0
        for char in import_string:
            if char == '.':
                dots_count += 1
            else:
                break

        if dots_count > 0:
            # Relative import
            try:
                current_dir = os.path.dirname(os.path.abspath(current_filepath))
                target_dir = current_dir
                for _ in range(dots_count - 1):
                    target_dir = os.path.dirname(target_dir)

                remaining = import_string[dots_count:]
                if remaining:
                    parts = remaining.split('.')
                    target_path = os.path.join(target_dir, *parts)
                else:
                    target_path = target_dir

                py_file = target_path + '.py'
                if os.path.isfile(py_file):
                    return os.path.normpath(os.path.abspath(py_file))

                init_file = os.path.join(target_path, '__init__.py')
                if os.path.isfile(init_file):
                    return os.path.normpath(os.path.abspath(init_file))
            except OSError:
                pass
        else:
            # Absolute import
            parts = import_string.split('.')
            try:
                current_dir = os.path.dirname(os.path.abspath(current_filepath))
                temp_dir = current_dir
                while True:
                    candidate_path = os.path.join(temp_dir, *parts)
                    py_file = candidate_path + '.py'
                    if os.path.isfile(py_file):
                        return os.path.normpath(os.path.abspath(py_file))

                    init_file = os.path.join(candidate_path, '__init__.py')
                    if os.path.isfile(init_file):
                        return os.path.normpath(os.path.abspath(init_file))

                    parent_dir = os.path.dirname(temp_dir)
                    if parent_dir == temp_dir:
                        break
                    temp_dir = parent_dir
            except OSError:
                pass

        return None
