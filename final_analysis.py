#!/usr/bin/env python3
import ast
import os
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple

def analyze_file(filepath: Path) -> Tuple[List[str], List[str]]:
    """Analyze a file for imports and find potentially unused ones."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Skip files with syntax errors
        return [], []
    
    imports = []
    imported_names = set()
    
    # Collect imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                imported_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                full_name = f"{module}.{alias.name}" if module else alias.name
                imports.append(full_name)
                imported_names.add(alias.asname or alias.name)
    
    # Check for usage in the code (simple string search)
    unused = []
    for imp in imports:
        # Skip if it's a module import (like "os", "sys") - harder to detect usage
        if '.' not in imp:
            # For simple imports, check if the module name appears
            module_name = imp.split('.')[0]
            if module_name not in content.replace('import', '').replace('from', ''):
                # More careful check - look for module.attribute patterns
                lines = content.split('\n')
                used = False
                for line in lines:
                    if 'import' in line or 'from' in line:
                        continue
                    if module_name in line and not line.strip().startswith('#'):
                        used = True
                        break
                if not used:
                    unused.append(imp)
        else:
            # For from imports, check if the imported name is used
            imported_name = imp.split('.')[-1]
            if imported_name not in content.replace('import', '').replace('from', ''):
                unused.append(imp)
    
    return imports, unused

def main():
    app_dir = Path("app")
    python_files = list(app_dir.rglob("*.py"))
    
    print("Analysis of Python files in app/ directory:\n")
    print("=" * 80)
    
    all_unused = []
    
    for filepath in sorted(python_files):
        if filepath.name == "__init__.py":
            continue
            
        imports, unused = analyze_file(filepath)
        
        if unused:
            print(f"\n{filepath}:")
            print(f"  Total imports: {len(imports)}")
            print(f"  Potentially unused: {len(unused)}")
            for imp in sorted(unused):
                print(f"    - {imp}")
            all_unused.append((filepath, unused))
    
    if not all_unused:
        print("\nNo potentially unused imports found!")
    else:
        print(f"\n\nSummary: Found {len(all_unused)} files with potentially unused imports")
        
    print("\n" + "=" * 80)
    print("\nNote: This is a conservative analysis. Some imports may be used in:")
    print("  - Type hints (should be kept)")
    print("  - __all__ lists (should be kept)")
    print("  - Dynamic imports or eval() statements")
    print("  - Docstrings or comments")
    print("\nAlways verify manually before removing imports.")

if __name__ == "__main__":
    main()
