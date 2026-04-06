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
Analyze Python files to find unused functions.
This script will identify all function definitions and check if they're called anywhere.
"""

import re
import os
from pathlib import Path
from collections import defaultdict

# Files to analyze
SRC_DIR = Path("src")
MAIN_FILE = Path("main.py")

# Patterns to find function definitions
FUNC_DEF_PATTERN = r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
CLASS_DEF_PATTERN = r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)'

# Pattern to find function calls (simplified)
# This will catch func(), self.func(), obj.func(), module.func()
FUNC_CALL_PATTERN = r'[.\s]([a-zA-Z_][a-zA-Z0-9_]*)\s*\('

def extract_functions_from_file(filepath):
    """Extract all function definitions from a Python file."""
    functions = []
    current_class = None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            # Check for class definition
            class_match = re.match(CLASS_DEF_PATTERN, line)
            if class_match:
                current_class = class_match.group(1)
                continue
            
            # Check for function definition
            func_match = re.match(FUNC_DEF_PATTERN, line)
            if func_match:
                func_name = func_match.group(1)
                
                # Skip magic methods and private methods starting with __
                if func_name.startswith('__') and func_name.endswith('__'):
                    continue
                
                functions.append({
                    'name': func_name,
                    'line': line_num,
                    'class': current_class,
                    'file': str(filepath)
                })
    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return functions

def find_function_calls_in_file(filepath):
    """Find all function calls in a Python file."""
    calls = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all function calls
        matches = re.findall(FUNC_CALL_PATTERN, content)
        calls.update(matches)
    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return calls

def analyze_unused_functions():
    """Main analysis function."""
    print("="*80)
    print("ANALYZING UNUSED FUNCTIONS IN SCHOOL BELL APP")
    print("="*80)
    print()
    
    # Collect all Python files
    python_files = []
    
    # Add main.py
    if MAIN_FILE.exists():
        python_files.append(MAIN_FILE)
    
    # Add all files from src/
    if SRC_DIR.exists():
        for py_file in SRC_DIR.glob("*.py"):
            python_files.append(py_file)
    
    print(f"Analyzing {len(python_files)} Python files:")
    for pf in python_files:
        print(f"  - {pf}")
    print()
    
    # Step 1: Extract all function definitions
    all_functions = []
    functions_by_file = defaultdict(list)
    
    for py_file in python_files:
        funcs = extract_functions_from_file(py_file)
        all_functions.extend(funcs)
        functions_by_file[str(py_file)].extend(funcs)
    
    print(f"Total functions found: {len(all_functions)}")
    print()
    
    # Step 2: Find all function calls across all files
    all_calls = set()
    
    for py_file in python_files:
        calls = find_function_calls_in_file(py_file)
        all_calls.update(calls)
    
    print(f"Total unique function names called: {len(all_calls)}")
    print()
    
    # Step 3: Identify unused functions
    unused_functions = []
    
    for func in all_functions:
        func_name = func['name']
        
        # Skip if it's a special method or common overrides
        if func_name in ['__init__', '__str__', '__repr__', 'setup', 'main']:
            continue
        
        # Check if function name appears in any calls
        if func_name not in all_calls:
            unused_functions.append(func)
    
    # Step 4: Display results
    print("="*80)
    print(f"UNUSED FUNCTIONS FOUND: {len(unused_functions)}")
    print("="*80)
    print()
    
    if unused_functions:
        # Group by file
        by_file = defaultdict(list)
        for func in unused_functions:
            by_file[func['file']].append(func)
        
        for filepath in sorted(by_file.keys()):
            filename = os.path.basename(filepath)
            funcs = by_file[filepath]
            
            print(f"\n{filename}:")
            print("-" * 80)
            
            for func in sorted(funcs, key=lambda x: x['line']):
                if func['class']:
                    print(f"  - {func['class']}.{func['name']} (line {func['line']})")
                else:
                    print(f"  - {func['name']} (line {func['line']})")
    else:
        print("No unused functions found!")
    
    print()
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    # Additional statistics
    print()
    print("STATISTICS:")
    print(f"  Total functions defined: {len(all_functions)}")
    print(f"  Functions called: {len(all_functions) - len(unused_functions)}")
    print(f"  Unused functions: {len(unused_functions)}")
    print(f"  Usage rate: {((len(all_functions) - len(unused_functions)) / len(all_functions) * 100):.1f}%")
    
    return unused_functions

if __name__ == "__main__":
    unused = analyze_unused_functions()
