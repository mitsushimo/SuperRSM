import pathlib
import ast

ui_plotting_keywords = {'tkinter', 'ttk', 'matplotlib', 'pyplot', 'seaborn', 'plotly', 'bokeh', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6'}

paths = list(pathlib.Path('super_rsm').rglob('*.py'))

findings = []
for p in paths:
    code = p.read_text(encoding='utf-8')
    tree = ast.parse(code, filename=str(p))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for kw in ui_plotting_keywords:
                    if kw in alias.name:
                        findings.append((p.as_posix(), alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for kw in ui_plotting_keywords:
                if kw in mod:
                    findings.append((p.as_posix(), mod, node.lineno))

if findings:
    print(f"FOUND UI/PLOTTING IMPORTS: {len(findings)}")
    for f in findings:
        print(f"  {f[0]}:{f[2]} -> {f[1]}")
else:
    print("ZERO UI/plotting imports found across all modules in super_rsm!")
