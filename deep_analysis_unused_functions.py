# Copyright (C) 2026  Ali Qasem
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Deep analysis of unused functions.
This performs a more thorough analysis by tracking actual function usage patterns.
"""

import ast
import os
from pathlib import Path
from collections import defaultdict

SRC_DIR = Path("src")
MAIN_FILE = Path("main.py")

class FunctionCollector(ast.NodeVisitor):
    """Collect all function and method definitions."""
    
    def __init__(self, filename):
        self.filename = filename
        self.functions = []
        self.current_class = None
        self.class_stack = []
    
    def visit_ClassDef(self, node):
        self.class_stack.append(node.name)
        self.current_class = node.name
        self.generic_visit(node)
        self.class_stack.pop()
        self.current_class = self.class_stack[-1] if self.class_stack else None
    
    def visit_FunctionDef(self, node):
        # Skip magic methods
        if not (node.name.startswith('__') and node.name.endswith('__')):
            self.functions.append({
                'name': node.name,
                'line': node.lineno,
                'class': self.current_class,
                'file': self.filename,
                'is_method': self.current_class is not None,
                'full_name': f"{self.current_class}.{node.name}" if self.current_class else node.name
            })
        self.generic_visit(node)

class FunctionCallCollector(ast.NodeVisitor):
    """Collect all function and method calls."""
    
    def __init__(self):
        self.calls = set()
    
    def visit_Call(self, node):
        # Handle different types of calls
        if isinstance(node.func, ast.Name):
            # Direct function call: func()
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Method call: obj.method() or self.method()
            self.calls.add(node.func.attr)
            # Also check if it's a module.function call
            if isinstance(node.func.value, ast.Name):
                self.calls.add(f"{node.func.value.id}.{node.func.attr}")
        
        self.generic_visit(node)

def parse_file(filepath):
    """Parse a Python file and return its AST."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return ast.parse(content, filename=str(filepath))
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

def collect_all_functions():
    """Collect all function definitions from all Python files."""
    all_files = []
    
    if MAIN_FILE.exists():
        all_files.append(MAIN_FILE)
    
    if SRC_DIR.exists():
        for py_file in SRC_DIR.glob("*.py"):
            if py_file.name != "__init__.py":
                all_files.append(py_file)
    
    all_functions = []
    
    for filepath in all_files:
        tree = parse_file(filepath)
        if tree:
            collector = FunctionCollector(str(filepath))
            collector.visit(tree)
            all_functions.extend(collector.functions)
    
    return all_functions, all_files

def collect_all_calls(files):
    """Collect all function calls from all Python files."""
    all_calls = set()
    
    for filepath in files:
        tree = parse_file(filepath)
        if tree:
            collector = FunctionCallCollector()
            collector.visit(tree)
            all_calls.update(collector.calls)
    
    return all_calls

def analyze_unused():
    """Perform deep analysis of unused functions."""
    print("="*80)
    print("DEEP ANALYSIS OF UNUSED FUNCTIONS")
    print("="*80)
    print()
    
    # Step 1: Collect all function definitions
    all_functions, all_files = collect_all_functions()
    
    print(f"Files analyzed: {len(all_files)}")
    for f in all_files:
        print(f"  - {f}")
    print()
    print(f"Total functions found: {len(all_functions)}")
    print()
    
    # Step 2: Collect all function calls
    all_calls = collect_all_calls(all_files)
    
    print(f"Total unique names called: {len(all_calls)}")
    print()
    
    # Step 3: Identify potentially unused functions
    unused = []
    potentially_unused = []
    
    # Special names that are used implicitly (Qt signals, callbacks, etc.)
    implicit_usage = {
        # Qt event handlers
        'closeEvent', 'showEvent', 'hideEvent', 'paintEvent', 'resizeEvent',
        # Qt signal handlers (connected via .connect())
        'timeout', 'clicked', 'triggered', 'valueChanged', 'currentTextChanged',
        'stateChanged', 'itemChanged', 'cellClicked', 'accepted', 'rejected',
        # Entry points
        'main', 'setup_menus', 'setup_logging',
        # Special methods often called indirectly
        'get_time', 'exec', 'show', 'hide',
    }
    
    for func in all_functions:
        func_name = func['name']
        
        # Check various usage patterns
        is_called = (
            func_name in all_calls or                    # Direct name match
            func['full_name'] in all_calls or            # Class.method match
            any(func_name in call for call in all_calls) # Substring match
        )
        
        # Check if it's an implicit usage
        is_implicit = func_name in implicit_usage
        
        # Check if it's a property or decorator
        is_property_like = func_name.startswith('get_') or func_name.startswith('set_')
        
        if not is_called and not is_implicit:
            if is_property_like or func['is_method']:
                potentially_unused.append(func)
            else:
                unused.append(func)
    
    # Display results
    print("="*80)
    print("RESULTS")
    print("="*80)
    print()
    
    # Definitely unused functions
    if unused:
        print(f"DEFINITELY UNUSED FUNCTIONS: {len(unused)}")
        print("-"*80)
        by_file = defaultdict(list)
        for func in unused:
            by_file[func['file']].append(func)
        
        for filepath in sorted(by_file.keys()):
            filename = os.path.basename(filepath)
            print(f"\n{filename}:")
            for func in sorted(by_file[filepath], key=lambda x: x['line']):
                if func['class']:
                    print(f"  - {func['class']}.{func['name']} (line {func['line']})")
                else:
                    print(f"  - {func['name']} (line {func['line']})")
    else:
        print("NO DEFINITELY UNUSED FUNCTIONS FOUND")
    
    print()
    
    # Potentially unused (needs manual review)
    if potentially_unused:
        print(f"\nPOTENTIALLY UNUSED (Manual Review Needed): {len(potentially_unused)}")
        print("-"*80)
        by_file = defaultdict(list)
        for func in potentially_unused:
            by_file[func['file']].append(func)
        
        for filepath in sorted(by_file.keys()):
            filename = os.path.basename(filepath)
            print(f"\n{filename}:")
            for func in sorted(by_file[filepath], key=lambda x: x['line']):
                if func['class']:
                    print(f"  - {func['class']}.{func['name']} (line {func['line']})")
                else:
                    print(f"  - {func['name']} (line {func['line']})")
    else:
        print("NO POTENTIALLY UNUSED FUNCTIONS")
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total functions: {len(all_functions)}")
    print(f"Definitely unused: {len(unused)}")
    print(f"Potentially unused: {len(potentially_unused)}")
    print(f"Confirmed used: {len(all_functions) - len(unused) - len(potentially_unused)}")
    print()
    
    return unused, potentially_unused

if __name__ == "__main__":
    unused, potentially = analyze_unused()
