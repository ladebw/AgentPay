#!/usr/bin/env python3
import ast
import os
import sys
from pathlib import Path
from typing import Set, List, Tuple, Dict

def get_imports_and_usage(filepath: Path) -> Tuple[Dict[str, str], Set[str]]:
    """Get imports and used names from a Python file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    imports = {}  # name -> full_import
    used_names = set()
    
    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                imports[alias.asname or alias.name] = alias.name
                
        def visit_ImportFrom(self, node):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                full_name = f"{module}.{alias.name}" if module else alias.name
                imports[alias.asname or alias.name] = full_name
        
        def visit_Name(self, node):
            if isinstance(node.ctx, (ast.Load, ast.Store)):
                used_names.add(node.id)
        
        def visit_Attribute(self, node):
            # Collect attribute chains
            try:
                parts = []
                current = node
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                    # Add all prefixes
                    for i in range(1, len(parts) + 1):
                        used_names.add(".".join(parts[:i]))
            except:
                pass
    
    visitor = ImportVisitor()
    visitor.visit(tree)
    
    return imports, used_names

def check_file(filepath: Path) -> List[str]:
    """Check a file for unused imports."""
    imports, used_names = get_imports_and_usage(filepath)
    
    unused = []
    for name, full_import in imports.items():
        # Check if name is used
        if name not in used_names:
            # Check if any prefix of the import is used
            is_used = False
            for used in used_names:
                if used.startswith(name + ".") or name.startswith(used + "."):
                    is_used = True
                    break
                # Check for module.submodule.Class pattern
                if "." in full_import:
                    base_module = full_import.split(".")[0]
                    if base_module == used or used.startswith(base_module + "."):
                        is_used = True
                        break
            
            if not is_used:
                unused.append(f"{name} (from {full_import})")
    
    return unused

def main():
    app_dir = Path("app")
    python_files = list(app_dir.rglob("*.py"))
    
    print(f"Analyzing {len(python_files)} Python files in {app_dir}...\n")
    
    files_with_unused = []
    
    for filepath in sorted(python_files):
        # Skip __init__.py files as they often have imports for re-export
        if filepath.name == "__init__.py":
            continue
            
        unused = check_file(filepath)
        if unused:
            files_with_unused.append((filepath, unused))
    
    if not files_with_unused:
        print("No unused imports found!")
        return
    
    print("Files with potentially unused imports:\n")
    for filepath, unused in files_with_unused:
        print(f"{filepath}:")
        for imp in sorted(unused):
            print(f"  - {imp}")
        print()

if __name__ == "__main__":
    main()
