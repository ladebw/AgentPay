#!/usr/bin/env python3
import ast
import os
import sys
from pathlib import Path
from typing import Set, List, Tuple, Dict, Optional

class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.imports = set()  # All imported names
        self.used_names = set()  # All names used in the code
        self.type_hint_names = set()  # Names used in type hints
        self.all_names = set()  # Names in __all__ if present
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
            if alias.asname:
                self.imports.add(alias.asname)
    
    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports.add(full_name)
            if alias.asname:
                self.imports.add(alias.asname)
            else:
                self.imports.add(alias.name)
    
    def visit_Name(self, node):
        self.used_names.add(node.id)
    
    def visit_Attribute(self, node):
        # Track attribute access like module.Class
        try:
            # Try to get the full attribute chain
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
                full_name = ".".join(reversed(parts))
                self.used_names.add(full_name)
        except:
            pass
    
    def visit_AnnAssign(self, node):
        # Track type hints
        if node.annotation:
            self._extract_type_hint_names(node.annotation)
    
    def visit_FunctionDef(self, node):
        # Track return type hints
        if node.returns:
            self._extract_type_hint_names(node.returns)
        # Track argument type hints
        for arg in node.args.args:
            if arg.annotation:
                self._extract_type_hint_names(arg.annotation)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        if node.returns:
            self._extract_type_hint_names(node.returns)
        for arg in node.args.args:
            if arg.annotation:
                self._extract_type_hint_names(arg.annotation)
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        # Check for __all__ assignments
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Str):
                            self.all_names.add(elt.s)
                        elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            self.all_names.add(elt.value)
        self.generic_visit(node)
    
    def _extract_type_hint_names(self, node):
        """Extract names from type hints."""
        if isinstance(node, ast.Name):
            self.type_hint_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            try:
                parts = []
                current = node
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                    full_name = ".".join(reversed(parts))
                    self.type_hint_names.add(full_name)
            except:
                pass
        elif isinstance(node, ast.Subscript):
            self._extract_type_hint_names(node.value)
            if node.slice:
                if isinstance(node.slice, ast.Index):
                    self._extract_type_hint_names(node.slice.value)
                elif hasattr(node.slice, 'value'):
                    self._extract_type_hint_names(node.slice.value)
        elif isinstance(node, ast.Tuple):
            for elt in node.elts:
                self._extract_type_hint_names(elt)

def analyze_file(filepath: Path) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """Analyze a Python file for imports and their usage."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)
        
        return analyzer.imports, analyzer.used_names, analyzer.type_hint_names, analyzer.all_names
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}", file=sys.stderr)
        return set(), set(), set(), set()

def find_unused_imports(filepath: Path) -> List[str]:
    """Find unused imports in a Python file."""
    imports, used_names, type_hint_names, all_names = analyze_file(filepath)
    
    # Convert imports to simple names for comparison
    import_names = set()
    import_map = {}  # Map simple name to full import
    
    for imp in imports:
        # Handle different import formats
        if '.' in imp:
            # For imports like "app.schemas.agent", track both full and base
            parts = imp.split('.')
            import_names.add(parts[0])  # Base module
            import_names.add(imp)       # Full import
            import_map[parts[0]] = imp
            import_map[imp] = imp
        else:
            import_names.add(imp)
            import_map[imp] = imp
    
    # Names that should be kept (used in code or type hints or __all__)
    keep_names = used_names.union(type_hint_names).union(all_names)
    
    # Find unused imports
    unused = []
    for imp in sorted(imports):
        # Get the base name for checking
        base_name = imp.split('.')[0] if '.' in imp else imp
        
        # Check if this import or its base is used
        is_used = False
        for keep in keep_names:
            if keep == imp or keep.startswith(imp + '.') or imp.startswith(keep + '.'):
                is_used = True
                break
            # Also check base name
            if keep == base_name or keep.startswith(base_name + '.'):
                is_used = True
                break
        
        if not is_used:
            unused.append(imp)
    
    return unused

def main():
    app_dir = Path("app")
    python_files = list(app_dir.rglob("*.py"))
    
    print(f"Analyzing {len(python_files)} Python files in {app_dir}...\n")
    
    files_with_unused = []
    
    for filepath in sorted(python_files):
        unused = find_unused_imports(filepath)
        if unused:
            files_with_unused.append((filepath, unused))
    
    if not files_with_unused:
        print("No unused imports found!")
        return
    
    print("Files with unused imports:\n")
    for filepath, unused in files_with_unused:
        print(f"{filepath}:")
        for imp in sorted(unused):
            print(f"  - {imp}")
        print()

if __name__ == "__main__":
    main()
