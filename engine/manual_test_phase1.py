import os
import sys

# Add the project root directory to the python path
# WHY: This allows running this script from the project root or engine directory 
# without encountering import errors for the engine package modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.resolvers.js_ts_resolver import JSTSResolver

def main():
    # WHY: Determine paths dynamically so that the script runs reliably from any Cwd.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    auth_js_path = os.path.join(project_root, 'fixture_repo', 'auth.js')
    
    print("--- RippleGuard Manual Test (Phase 1) ---")
    print(f"Target File: {auth_js_path}\n")
    
    # 1. Instantiate JSTSResolver
    # WHY: Instantiate resolver to parse and analyze JavaScript files.
    resolver = JSTSResolver()
    
    # 2. Parse the target file
    # WHY: Test parse_file to verify tree-sitter successfully reads and parses JS syntax.
    print("[1] Parsing file...")
    ast = resolver.parse_file(auth_js_path)
    if ast is None:
        print("ERROR: Parsing failed.")
        sys.exit(1)
    print("Success: AST parsed.\n")
    
    # 3. Extract and print imports
    # WHY: Test extract_imports to verify JSTSResolver extracts ES module imports correctly.
    print("[2] Extracting imports:")
    imports = resolver.extract_imports(ast)
    for imp in imports:
        print(imp)
    print()
    
    # 4. Resolve imports to physical file paths
    # WHY: Test resolve_import_to_filepath to verify JSTSResolver maps relative imports to real files.
    print("[3] Resolving import paths:")
    for imp in imports:
        resolved = resolver.resolve_import_to_filepath(imp, auth_js_path)
        print(f"Import: '{imp}' -> Resolved: '{resolved}'")
    print()
        
    # 5. Extract function calls
    # WHY: Test extract_function_calls to verify JSTSResolver extracts identifier function calls.
    print("[4] Extracting function calls:")
    calls = resolver.extract_function_calls(ast)
    for call in calls:
        print(call)
    print("-----------------------------------------")

if __name__ == "__main__":
    main()
