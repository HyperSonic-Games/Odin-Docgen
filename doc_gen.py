import os
import re
import html
import argparse

# Default ignore dirs and extensions
DEFAULT_IGNORE_DIRS = {"build", "docs", "out", ".git"}
SOURCE_EXTENSIONS = {".odin"}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
    :root {{
        --bg: #ffffff;
        --fg: #000000;
        --code-bg: #f0f0f0;
    }}
    [data-theme="dark"] {{
        --bg: #1e1e1e;
        --fg: #e0e0e0;
        --code-bg: #2e2e2e;
    }}
    body {{
        background: var(--bg);
        color: var(--fg);
        font-family: sans-serif;
        padding: 2em;
        max-width: 900px;
        margin: auto;
    }}
    pre, code {{
        background: var(--code-bg);
        color: var(--fg);
        font-family: monospace;
        padding: 0.5em;
        border-radius: 5px;
        overflow-x: auto;
        display: block;
    }}
    .theme-toggle {{
        position: fixed;
        top: 1em;
        right: 1em;
        background: none;
        border: 1px solid var(--fg);
        padding: 0.4em;
        color: var(--fg);
        cursor: pointer;
        border-radius: 5px;
    }}
</style>
</head>
<body>
<button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">
<svg id="theme-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor">
    <circle cx="12" cy="12" r="5"/>
    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
</svg>
</button>

<h1>{title}</h1>
{entries}

<script>
    const sunSVG = `{sun_svg}`;
    const moonSVG = `{moon_svg}`;

    function setTheme(theme) {{
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        document.getElementById('theme-icon').outerHTML = theme === 'dark' ? moonSVG : sunSVG;
    }}

    function toggleTheme() {{
        const current = localStorage.getItem('theme') || 'light';
        setTheme(current === 'dark' ? 'light' : 'dark');
    }}

    (function() {{
        const saved = localStorage.getItem('theme') || 'light';
        setTheme(saved);
    }})();
</script>
</body>
</html>
"""

sun_svg = """<svg id="theme-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor">
<circle cx="12" cy="12" r="5"/>
<path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
</svg>"""

moon_svg = """<svg id="theme-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor">
<path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/>
</svg>"""

def extract_docs(file_content):
    pattern = re.compile(
        r"/\*\*(.*?)\*/\s*([A-Za-z0-9_]+)\s*::\s*proc\s*\((.*?)\)",
        re.DOTALL
    )
    matches = pattern.findall(file_content)
    docs = []
    for doc, name, args in matches:
        doc_lines = [line.strip(" *") for line in doc.strip().splitlines()]
        doc_html = "<br>".join(html.escape(line) for line in doc_lines)
        sig = f"{name}({args})"
        docs.append(f"<h2>{name}</h2><p>{doc_html}</p><pre><code>{html.escape(sig)}</code></pre>")
    return docs

def scan_dir_and_generate(source_dir, output_dir, ignore_dirs):
    os.makedirs(output_dir, exist_ok=True)

    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            if any(file.endswith(ext) for ext in SOURCE_EXTENSIONS):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                docs = extract_docs(content)
                if not docs:
                    continue
                rel_name = os.path.relpath(path, source_dir).replace(os.sep, "_")
                out_path = os.path.join(output_dir, rel_name + ".html")
                with open(out_path, "w", encoding="utf-8") as out:
                    out.write(HTML_TEMPLATE.format(
                        title=html.escape(path),
                        entries="\n".join(docs),
                        sun_svg=sun_svg,
                        moon_svg=moon_svg
                    ))

def main():
    parser = argparse.ArgumentParser(description="Generates HTML docs from odin code")
    parser.add_argument("-s", "--source", default=".", help="Source directory to scan")
    parser.add_argument("-o", "--output", default="docs", help="Output directory for HTML files")
    parser.add_argument("-i", "--ignore", default="build,docs,out,.git,third_party,dist", help="Comma-separated directories to ignore")

    args = parser.parse_args()
    ignore_dirs = set(x.strip() for x in args.ignore.split(",") if x.strip())

    scan_dir_and_generate(args.source, args.output, ignore_dirs)
    print(f"Documentation generated in: {args.output}")

if __name__ == "__main__":
    main()
