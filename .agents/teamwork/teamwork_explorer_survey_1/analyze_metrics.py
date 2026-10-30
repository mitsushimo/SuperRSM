import ast
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

def analyze_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.splitlines()
    
    total_lines = len(lines)
    blank_lines = sum(1 for line in lines if not line.strip())
    comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
    code_lines = total_lines - blank_lines - comment_lines
    file_size = os.path.getsize(filename)
    
    tree = ast.parse(content)
    
    classes = []
    functions = []
    imports = []
    from_imports = []
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            classes.append({
                'name': node.name,
                'start': node.lineno,
                'end': node.end_lineno,
                'lines': node.end_lineno - node.lineno + 1,
                'methods': methods
            })
        elif isinstance(node, ast.FunctionDef):
            functions.append({
                'name': node.name,
                'start': node.lineno,
                'end': node.end_lineno,
                'lines': node.end_lineno - node.lineno + 1,
                'args': [a.arg for a in node.args.args]
            })
        elif isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            from_imports.append((node.module, [n.name for n in node.names]))
            
    return {
        'filename': filename,
        'total_lines': total_lines,
        'code_lines': code_lines,
        'blank_lines': blank_lines,
        'comment_lines': comment_lines,
        'file_size': file_size,
        'classes': classes,
        'functions': functions,
        'imports': imports,
        'from_imports': from_imports
    }

for f in ['rsm_backend.py', 'high_d_plotter.py', 'rsm_gui.py']:
    info = analyze_file(f)
    print('='*70)
    print(f"File: {info['filename']} ({info['file_size']} bytes)")
    print(f"Lines: Total={info['total_lines']}, Code={info['code_lines']}, Blank={info['blank_lines']}, Comment={info['comment_lines']}")
    print(f"Imports: {info['imports']}")
    print(f"From Imports: {info['from_imports']}")
    print(f"Classes ({len(info['classes'])}):")
    for c in info['classes']:
        print(f"  {c['name']}: lines {c['start']}-{c['end']} ({c['lines']} lines), methods={len(c['methods'])}")
    print(f"Top-level Functions ({len(info['functions'])}):")
    for fn in info['functions']:
        print(f"  {fn['name']}({', '.join(fn['args'])}): lines {fn['start']}-{fn['end']} ({fn['lines']} lines)")
