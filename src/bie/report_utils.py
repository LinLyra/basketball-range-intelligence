from pathlib import Path

def ensure_dirs(*paths):
    for p in paths: Path(p).mkdir(parents=True, exist_ok=True)

def save_markdown_report(text, path):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding='utf-8')
