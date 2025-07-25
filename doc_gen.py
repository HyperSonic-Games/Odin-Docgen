import re
import os
import argparse

def extract_docs(code):
    pattern = re.compile(
        r'(/\*([\s\S]*?)\*/)\s*([\w\d_]+)\s*::\s*proc\s*(\([^\)]*\))',
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

def generate_html(docs, filename):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Documentation for {filename}</title>
<style>
  body {{ background: #121212; color: #eee; font-family: Arial, sans-serif; padding: 2rem; }}
  h1 {{ color: #80cbc4; }}
  section {{ background: #1e1e1e; border-radius: 8px; padding: 1rem; margin-bottom: 2rem; box-shadow: 0 0 8px #000; }}
  h2 {{ color: #4db6ac; }}
  p {{ line-height: 1.5; }}
  pre {{ background: #263238; padding: 0.8em 1em; border-radius: 4px; overflow-x: auto; color: #cfd8dc; }}
  code {{ font-family: monospace; }}
  .params, .return {{ margin-top: 0.5em; }}
  .params ul {{ padding-left: 1.2em; }}
  .params li {{ margin-bottom: 0.3em; }}
  .param-name {{ font-weight: 600; color: #80cbc4; }}
  .return {{ font-weight: 600; color: #a5d6a7; margin-top: 1em; }}
  a {{ color: #80cbc4; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>Documentation for {filename}</h1>
"""
    for d in docs:
        html += f"<section>\n"
        html += f"  <h2>{d['func']}</h2>\n"
        html += f"  <pre><code>{d['func']} {d['signature']}</code></pre>\n"
        html += f"  <p>{d['description']}</p>\n"
        if d['params']:
            html += "  <div class='params'><strong>Parameters:</strong><ul>\n"
            for pname, pdesc in d['params']:
                html += f"    <li><span class='param-name'>{pname}</span>: {pdesc}</li>\n"
            html += "  </ul></div>\n"
        if d['return']:
            html += f"  <div class='return'>Returns: {d['return']}</div>\n"
        html += "</section>\n"

    html += "</body>\n</html>"
    return html

def generate_index_html(docs_list):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Util Package Documentation Index</title>
<style>
  body { background: #121212; color: #eee; font-family: Arial, sans-serif; padding: 2rem; }
  h1 { color: #80cbc4; }
  ul { list-style-type: none; padding-left: 0; }
  li { margin-bottom: 0.5rem; }
  a { text-decoration: none; color: #80cbc4; }
  a:hover { text-decoration: underline; }
</style>
</head>
<body>
<h1>Documentation Index</h1>
<ul>
"""
    for doc in docs_list:
        html += f'  <li><a href="{doc["filename"]}">{doc["filename"]}</a></li>\n'

    html += """
</ul>
</body>
</html>"""
    return html

def generate_docs_for_dir(src_dir, out_dir, ignore_dirs):
    docs_list = []
    src_dir = os.path.abspath(src_dir)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    for root, dirs, files in os.walk(src_dir):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if os.path.join(root, d) not in ignore_dirs_abs]
        for file in files:
            if file.endswith(".odin"):
                odin_path = os.path.join(root, file)
                with open(odin_path, "r", encoding="utf-8") as f:
                    code = f.read()
                docs = extract_docs(code)
                if not docs:
                    continue  # skip files with no docs
                html_filename = os.path.splitext(file)[0] + ".html"
                html_path = os.path.join(out_dir, html_filename)
                with open(html_path, "w", encoding="utf-8") as outf:
                    outf.write(generate_html(docs, file))

                docs_list.append({
                    "filename": html_filename
                })

                print(f"Generated {html_path}")

    index_path = os.path.join(out_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(generate_index_html(docs_list))

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

    # Build absolute ignore dir list
    ignore_dirs_abs = [os.path.abspath(os.path.join(args.src_dir, d)) for d in args.ignore]

    generate_docs_for_dir(args.src_dir, "./docs", ignore_dirs_abs)
