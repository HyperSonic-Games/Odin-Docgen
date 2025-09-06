import re
import os
import argparse
import html
from pathlib import Path, PurePosixPath

def extract_docs(code):
    pattern = re.compile(
        r'(/\*([\s\S]*?)\*/)\s*([\w\d_]+)\s*::\s*proc\s*(\([^\)]*\)(?:\s*->\s*[\w\d_]+)?)',
        re.MULTILINE
    )
    docs = []
    for match in pattern.finditer(code):
        full_comment = match.group(2).strip()
        func_name = match.group(3).strip()
        params_sig = match.group(4).strip()

        lines = [line.strip(" *") for line in full_comment.splitlines()]
        description = []
        params_list = []
        returns = ""
        for line in lines:
            if line.startswith("@param"):
                parts = line.split(None, 2)
                if len(parts) == 3:
                    _, pname, pdesc = parts
                    params_list.append((pname, pdesc))
                else:
                    params_list.append((line, ""))
            elif line.startswith("@return"):
                returns = line[len("@return"):].strip()
            else:
                description.append(line)

        docs.append({
            "func": func_name,
            "description": " ".join(description).strip(),
            "params": params_list,
            "return": returns,
            "signature": params_sig
        })
    return docs

def generate_html(docs, filename, sidebar_html="", current_file_path=None, out_dir=None):
    if current_file_path and out_dir:
        rel_index = os.path.relpath(out_dir / "index.html", start=Path(current_file_path).parent).replace("\\", "/")
    else:
        rel_index = "index.html"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Documentation for {filename}</title>
<style>
body {{ margin: 0; font-family: Arial, sans-serif; background: #121212; color: #eee; }}
a {{ text-decoration: none; color: #80cbc4; }}
a:hover {{ text-decoration: underline; }}
header {{ padding: 1rem; background: #1e1e1e; font-size: 1.5rem; color: #80cbc4; }}
main {{ display: flex; min-height: 100vh; }}
nav {{ width: 250px; background: #1e1e1e; padding: 1rem; overflow-y: auto; }}
nav details {{ margin-bottom: 0.5rem; }}
nav summary {{ cursor: pointer; user-select: none; }}
nav .file {{ display: block; }}
nav .folder::before {{ content: "📂 "; }}
nav .file::before {{ content: "📄 "; }}
nav .file.current a {{ font-weight: bold; color: #ffb74d; }}
article {{ flex: 1; padding: 2rem; }}
.back-index {{ margin-bottom: 1rem; }}
section {{ background: #1e1e1e; border-radius: 8px; padding: 1rem; margin-bottom: 2rem; box-shadow: 0 0 8px #000; }}
h2 {{ color: #4db6ac; }}
pre {{ background: #263238; padding: 0.8em 1em; border-radius: 4px; overflow-x: auto; color: #cfd8dc; }}
.code {{ font-family: monospace; }}
.params ul {{ padding-left: 1.2em; }}
.params li {{ margin-bottom: 0.3em; }}
.param-name {{ font-weight: 600; color: #80cbc4; }}
.return {{ font-weight: 600; color: #a5d6a7; margin-top: 1em; }}
</style>
</head>
<body>
<header>{filename}</header>
<main>
<nav>
{sidebar_html}
</nav>
<article>
<div class="back-index"><a href="{rel_index}">⬅ Back to Index</a></div>
"""
    for d in docs:
        html_content += f"<section>\n"
        html_content += f"  <h2>{html.escape(d['func'])}</h2>\n"
        html_content += f"  <pre class='code'>{html.escape(d['func'] + ' ' + d['signature'])}</pre>\n"
        html_content += f"  <p>{html.escape(d['description'])}</p>\n"
        if d['params']:
            html_content += "  <div class='params'><strong>Parameters:</strong><ul>\n"
            for pname, pdesc in d['params']:
                html_content += f"    <li><span class='param-name'>{html.escape(pname)}</span>: {html.escape(pdesc)}</li>\n"
            html_content += "  </ul></div>\n"
        if d['return']:
            html_content += f"  <div class='return'>Returns: {html.escape(d['return'])}</div>\n"
        html_content += "</section>\n"

    html_content += "</article>\n</main>\n</body>\n</html>"
    return html_content

def render_tree(d, current_file_path, out_dir, parent_path=Path("."), depth=0):
    html_tree = ""
    current_file_path = Path(current_file_path).resolve()

    for k, v in sorted(d.items()):
        indent = depth * 1.5
        style = f"padding-left: {indent}em;"
        if isinstance(v, dict):
            def has_current(child):
                for key, val in child.items():
                    if isinstance(val, dict):
                        if has_current(val):
                            return True
                    else:
                        target = Path(val).resolve()
                        if target == current_file_path:
                            return True
                return False
            open_attr = " open" if has_current(v) else ""
            html_tree += f"<details class='folder' style='{style}'{open_attr}><summary>{html.escape(k)}</summary>\n"
            html_tree += render_tree(v, current_file_path, out_dir, parent_path / k, depth + 1)
            html_tree += "</details>\n"
        else:
            target = Path(v).resolve()
            rel_link = os.path.relpath(target, start=Path(current_file_path).parent).replace("\\", "/")
            current_class = " class='current'" if target == current_file_path else ""
            html_tree += f'<div class="file"{current_class} style="{style}"><a href="{rel_link}">{html.escape(k)}</a></div>\n'
    return html_tree

def generate_docs_for_dir(src_dir, out_dir, ignore_dirs):
    docs_dict = {}
    src_dir = Path(src_dir).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build docs and sidebar tree
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if not any(Path(root, d).resolve().is_relative_to(Path(ignored)) for ignored in ignore_dirs)]
        for file in files:
            if file.endswith(".odin"):
                odin_path = Path(root) / file
                code = odin_path.read_text(encoding="utf-8")
                docs = extract_docs(code)
                if not docs:
                    continue

                rel_folder = Path(root).relative_to(src_dir)
                out_folder = out_dir / rel_folder
                out_folder.mkdir(parents=True, exist_ok=True)

                html_filename = file.replace(".odin", ".html")
                html_path = out_folder / html_filename

                # Build nested dict for sidebar with full resolved paths
                d = docs_dict
                for p in rel_folder.parts:
                    d = d.setdefault(p, {})
                d[file] = str(html_path.resolve())

                # Generate sidebar HTML
                sidebar_html = render_tree(docs_dict, current_file_path=str(html_path), out_dir=out_dir)

                html_content = generate_html(docs, file, sidebar_html=sidebar_html, current_file_path=str(html_path), out_dir=out_dir)
                html_path.write_text(html_content, encoding="utf-8")

                print(f"Generated {html_path}")

    # Generate index page
    index_path = out_dir / "index.html"
    sidebar_html = render_tree(docs_dict, current_file_path=str(index_path), out_dir=out_dir)
    index_path.write_text(generate_html([], "Index", sidebar_html=sidebar_html, current_file_path=str(index_path), out_dir=out_dir), encoding="utf-8")
    print(f"Generated index file at {index_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Odin docs as HTML with dark theme")
    parser.add_argument("src_dir", help="Source directory to scan recursively")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Directories to ignore (relative to src_dir), can be used multiple times"
    )
    args = parser.parse_args()

    ignore_dirs_abs = [str(Path(args.src_dir, d).resolve()) for d in args.ignore]

    generate_docs_for_dir(args.src_dir, "./docs", ignore_dirs_abs)
