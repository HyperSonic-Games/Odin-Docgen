import os
import re
import html
import argparse
from pathlib import Path

SUN_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon sun-icon"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'''
MOON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon moon-icon"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>'''

CSS = '''
body {
    font-family: Arial, sans-serif;
    margin: 2em;
    background-color: var(--bg);
    color: var(--fg);
    transition: background-color 0.3s, color 0.3s;
}
:root {
    --bg: #121212;
    --fg: #ddd;
    --tag-color: #66ccff;
    --code-bg: #222;
    --border-color: #444;
}
body.light {
    --bg: #fff;
    --fg: #222;
    --tag-color: #007acc;
    --code-bg: #f5f5f5;
    --border-color: #ccc;
}
.toggle-btn {
    position: fixed;
    top: 1em;
    right: 1em;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--fg);
    width: 2em;
    height: 2em;
}
h1, h2 {
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 0.3em;
}
pre {
    background-color: var(--code-bg);
    color: var(--fg);
    padding: 1em;
    overflow-x: auto;
    border-radius: 4px;
    font-family: monospace;
    white-space: pre-wrap;
    word-wrap: break-word;
}
code {
    font-family: monospace;
}
.tag-line {
    color: var(--tag-color);
    font-weight: bold;
    margin-top: 1em;
}
a {
    color: var(--tag-color);
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}

/* Keywords and operators */
.keyword { color: #cc99cd; font-weight: bold; }
.operator { color: #ffb86c; }
.string { color: #7ec699; }
.comment { color: #999; font-style: italic; }
'''

JS = f'''
function toggleTheme() {{
    const body = document.body;
    body.classList.toggle('light');
    localStorage.setItem('theme', body.classList.contains('light') ? 'light' : 'dark');
}}
document.addEventListener('DOMContentLoaded', () => {{
    if(localStorage.getItem('theme') === 'light') {{
        document.body.classList.add('light');
    }}
}});
'''

KEYWORDS = (
    "asm|auto_cast|bit_field|bit_set|break|case|cast|context|continue|defer|distinct|do|dynamic|else|enum|fallthrough|for|foreign|if|import|in|map|not_in|or_else|or_return|package|proc|return|struct|switch|transmute|typeid|union|using|when|where"
)

OPERATORS = [
    "=", "!", "^", "?", ":", "+", "-", "*", "/", "%", "%%", "&", "|", "~", "&~", "<<", ">>",
    "&&", "||",
    "+=", "-=", "*=", "/=", "%=", "%%=", "&=", "|=", "~=", "&~=", "<<=", ">>=",
    "&&=", "||=",
    "->", "---",
    "==", "!=", "<", ">", "<=", ">=",
    "(", ")", "[", "]", "{", "}",
    ":", "..", "..=", "..<",
    "#", "@", "$",
    ";", ".", ",",
    "++", "--"
]

# Escape operators for regex (except alphanum)
OPERATORS_RE = sorted(OPERATORS, key=len, reverse=True)
OPERATORS_RE = [re.escape(op) for op in OPERATORS_RE]
OPERATORS_RE_PATTERN = "(" + "|".join(OPERATORS_RE) + ")"

def syntax_highlight_c(code):
    code = html.escape(code)

    # Comments (// or /* */)
    code = re.sub(r"(//.*?$|/\*.*?\*/)", r'<span class="comment">\1</span>', code, flags=re.DOTALL | re.MULTILINE)

    # Strings (double quotes)
    code = re.sub(r'("([^"\\]|\\.)*")', r'<span class="string">\1</span>', code)

    # Keywords
    code = re.sub(r'\b(' + KEYWORDS + r')\b', r'<span class="keyword">\1</span>', code)

    # Operators
    code = re.sub(OPERATORS_RE_PATTERN, r'<span class="operator">\1</span>', code)

    return code

def parse_formatting(text):
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text

def format_doc_line(line):
    if line.startswith("@"):
        return f'<div class="tag-line">{html.escape(line)}</div>'
    else:
        return f'<p>{parse_formatting(line)}</p>'

def extract_doc_comments(file_path):
    entries = []
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except Exception:
        return entries

    # Match /** ... */ comments before proc/function
    pattern = re.compile(
        r'/\*\*(.*?)\*/\s*(proc|function)\s+([^\s(:]+)[^{;]*({[^}]*}|;)?',
        re.DOTALL
    )

    for m in pattern.finditer(content):
        doc_text = m.group(1).strip()
        name = m.group(3)
        code_block = m.group(4) or ""
        doc_lines = [line.strip(" *") for line in doc_text.splitlines() if line.strip()]
        entries.append((name, doc_lines, code_block.strip()))
    return entries

def generate_html_for_file(filename, docs, outdir):
    title = f"Docs for {filename}"
    content = f"<h1>{html.escape(filename)}</h1>\n"
    for name, doc_lines, code_block in docs:
        content += f"<h2>{html.escape(name)}</h2>\n"
        for line in doc_lines:
            content += format_doc_line(line)
        if code_block:
            content += f"<pre><code>{syntax_highlight_c(code_block)}</code></pre>\n"

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<style>{CSS}</style>
<script>{JS}</script>
</head>
<body>
<button class="toggle-btn" onclick="toggleTheme()" aria-label="Toggle dark/light mode">{MOON_SVG}</button>
{content}
</body>
</html>
"""
    out_path = Path(outdir) / (Path(filename).name + ".html")
    out_path.write_text(page, encoding="utf-8")

def generate_index_html(files, outdir):
    links = "".join(f'<li><a href="{html.escape(Path(f).name)}.html">{html.escape(f)}</a></li>\n' for f in sorted(files))
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Index of documentation</title>
<style>{CSS}</style>
<script>{JS}</script>
</head>
<body>
<button class="toggle-btn" onclick="toggleTheme()" aria-label="Toggle dark/light mode">{MOON_SVG}</button>
<h1>Documentation Index</h1>
<ul>
{links}
</ul>
</body>
</html>"""
    Path(outdir, "index.html").write_text(page, encoding="utf-8")

def scan_directory(rootdir, ignore_dirs):
    ignore_dirs = set(ignore_dirs)
    files = []
    for dirpath, dirnames, filenames in os.walk(rootdir):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for file in filenames:
            if file.endswith(".c") or file.endswith(".h"):  # adjust extensions if needed
                files.append(os.path.relpath(os.path.join(dirpath, file), rootdir))
    return files

def main():
    parser = argparse.ArgumentParser(description="Generate HTML docs from odin source code comments.")
    parser.add_argument("source_dir", help="Directory to scan for source files")
    parser.add_argument("output_dir", help="Directory to output HTML files")
    parser.add_argument("--ignore", nargs="*", default=[".git", "third_party", "build", "dist", "docs"], help="Directories to ignore")
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    files = scan_directory(args.source_dir, args.ignore)
    for file in files:
        docs = extract_doc_comments(os.path.join(args.source_dir, file))
        if docs:
            generate_html_for_file(file, docs, args.output_dir)
    generate_index_html(files, args.output_dir)

if __name__ == "__main__":
    main()
