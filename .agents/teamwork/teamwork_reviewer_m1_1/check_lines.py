import pathlib

files = [p for p in pathlib.Path('.').rglob('*.py') 
         if '.agents' not in p.parts and '.git' not in p.parts and '.pytest_cache' not in p.parts]

for p in sorted(files, key=lambda f: len(f.read_text(encoding='utf-8').splitlines()), reverse=True):
    lines = len(p.read_text(encoding='utf-8').splitlines())
    print(f"{lines:4d} lines : {p.as_posix()}")
