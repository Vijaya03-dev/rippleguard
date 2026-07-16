from abc import ABC, abstractmethod
from typing import Any, List, Optional

# WHY LanguageResolver is built this way:
# This abstract base class defines a standard interface for dependency analysis and code parsing.
# By decoupling language-specific AST parsing (like tree-sitter or regex-based tools) from the core 
# analysis engine, we can easily add support for other languages (e.g., Python, Java, Go) 
# by implementing a new concrete subclass, without having to rewrite or modify the downstream 
# dependency graph builder, scoring logic, API view layers, or extension controllers.
class LanguageResolver(ABC):

    @abstractmethod
    def parse_file(self, filepath: str) -> Any:
        """
        Parses a code file and returns its Abstract Syntax Tree (AST).
        
        WHY: Different languages require different parsers (e.g. tree-sitter, python's ast, javalang).
        Returning Any allows us to wrap any underlying AST structure (like tree-sitter Tree or python AST module node).
        
        Args:
            filepath: Absolute path to the source file to parse.
            
        Returns:
            The parsed AST/tree representation.
        """
        pass

    @abstractmethod
    def extract_imports(self, ast: Any) -> List[str]:
        """
        Walks the parsed AST and extracts raw import string literals.
        
        WHY: Before building a dependency graph, we need the raw import source strings (like './utils')
        specified in the code. This abstracts away how different languages define imports/modules.
        
        Args:
            ast: The AST returned by parse_file.
            
        Returns:
            A list of raw import strings found in the file.
        """
        pass

    @abstractmethod
    def extract_function_calls(self, ast: Any) -> List[str]:
        """
        Walks the parsed AST and extracts names of called functions.
        
        WHY: Function call analysis is crucial to map interaction patterns, dependencies, 
        or semantic coupling between files beyond simple imports in subsequent phases.
        
        Args:
            ast: The AST returned by parse_file.
            
        Returns:
            A list of name strings of the functions called within the file.
        """
        pass

    @abstractmethod
    def resolve_import_to_filepath(self, import_string: str, current_filepath: str) -> Optional[str]:
        """
        Resolves a raw import string to a concrete file path on disk relative to the current file.
        
        WHY: Source code imports are often relative paths (e.g. './utils') or lack extensions. 
        This method translates the import string into a clean, absolute path or resolves it 
        within the project environment, returning None if the import is external (like third-party libs)
        or cannot be resolved.
        
        Args:
            import_string: The raw import path/package string.
            current_filepath: The path of the file that contains this import.
            
        Returns:
            The absolute path of the resolved file on disk as a string, or None.
        """
        pass
