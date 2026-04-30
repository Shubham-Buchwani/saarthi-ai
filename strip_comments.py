import os
import re

def strip_python_comments(content):
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if line.strip().startswith('#'):
            continue
        new_lines.append(line)
    return '\n'.join(new_lines)

def strip_js_comments(content):
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if line.strip().startswith('//'):
            continue
        line = re.sub(r'(?<!:)\/\/.*', '', line)
        new_lines.append(line)

    return '\n'.join(new_lines)

def main():
    root_dir = r"d:\Saarthi AI"
    exclude_dirs = {'.git', 'node_modules', '.next', '__pycache__', 'venv', 'env', '.venv', 'dist', 'build', '.vscode', '.gemini'}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for file in filenames:
            ext = os.path.splitext(file)[1]
            filepath = os.path.join(dirpath, file)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                new_content = content
                if ext == '.py':
                    new_content = strip_python_comments(content)
                elif ext in {'.js', '.jsx', '.ts', '.tsx', '.css'}:
                    new_content = strip_js_comments(content)

                if new_content != content:
                    new_content = re.sub(r'\n\s*\n', '\n\n', new_content)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Stripped comments from: {filepath}")
            except Exception as e:
                pass

if __name__ == "__main__":
    main()
