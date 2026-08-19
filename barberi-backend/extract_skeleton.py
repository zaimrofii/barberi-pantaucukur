#!/usr/bin/env python3
import ast
import os
import re
import sys
import argparse
from pathlib import Path

# ==========================================
# 1. AST DEEP CONTRACT ANALYZER (PYTHON)
# ==========================================
class RichSchemaAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.payload_in_keys = set()
        self.response_out_keys = set()
        self.db_ops = set()
        self.side_effects = set()
        self.return_shapes = set()
        self.class_states = set()

    def _get_full_attr(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_full_attr(node.value)}.{node.attr}"
        return ""

    def visit_Assign(self, node):
        # Tangkap state kelas: self.attr = ...
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                if target.value.id == 'self':
                    self.class_states.add(target.attr)
        self.generic_visit(node)

    def visit_Return(self, node):
        if node.value:
            if isinstance(node.value, ast.Dict):
                keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
                if keys:
                    self.return_shapes.add(f"Dict{{ {', '.join(keys)} }}")
            elif isinstance(node.value, ast.Tuple):
                elts = [self._get_full_attr(e) or type(e).__name__ for e in node.value.elts]
                self.return_shapes.add(f"Tuple({', '.join(elts)})")
            elif isinstance(node.value, (ast.Name, ast.Attribute)):
                self.return_shapes.add(f"Var:{self._get_full_attr(node.value)}")
            elif isinstance(node.value, ast.Constant):
                self.return_shapes.add(f"Literal:{type(node.value.value).__name__}")
        self.generic_visit(node)

    def visit_Call(self, node):
        func_expr = self._get_full_attr(node.func)
        
        # Django payload detection
        if func_expr.endswith('.get') and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                caller = self._get_full_attr(node.func.value) if isinstance(node.func, ast.Attribute) else ""
                if any(k in caller for k in ['data', 'payload', 'request', 'GET', 'POST', 'body']):
                    self.payload_in_keys.add(first_arg.value)

        elif func_expr == 'JsonResponse' and node.args:
            if isinstance(node.args[0], ast.Dict):
                for key in node.args[0].keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        self.response_out_keys.add(key.value)

        elif ".objects." in func_expr or func_expr.endswith(('.save', '.delete', '.update')):
            self.db_ops.add(func_expr)

        elif any(kw in func_expr.upper() for kw in ['REDIS', 'CHANNEL', 'CONFIG', 'CACHE', 'SEND', 'LOG', 'REPORT', 'NETWORK']):
            self.side_effects.add(func_expr)

        self.generic_visit(node)


class PythonRichTransformer(ast.NodeTransformer):
    def visit_ClassDef(self, node):
        # Kumpulkan atribut class dari __init__
        analyzer = RichSchemaAnalyzer()
        analyzer.visit(node)
        
        self.generic_visit(node)
        
        if analyzer.class_states:
            doc = ast.get_docstring(node) or ""
            state_info = f"[CLASS STATE / ATTRS]: {', '.join(sorted(analyzer.class_states))}"
            new_doc = f"{doc}\n{'-'*40}\n{state_info}" if doc else state_info
            
            # Sisipkan docstring terupdate ke Class
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                node.body[0].value.value = new_doc
            else:
                node.body.insert(0, ast.Expr(value=ast.Constant(value=new_doc)))
        return node

    def visit_FunctionDef(self, node):
        analyzer = RichSchemaAnalyzer()
        analyzer.visit(node)
        
        existing_doc = ast.get_docstring(node) or ""
        contract_lines = []
        
        # 1. Parameter Input dengan Signature Lengkap
        args_str = []
        for arg in node.args.args:
            if arg.arg not in ['self', 'cls']:
                anno = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
                args_str.append(f"{arg.arg}{anno}")
        
        if analyzer.payload_in_keys:
            contract_lines.append(f"[HTTP PAYLOAD IN]: {', '.join(sorted(analyzer.payload_in_keys))}")
        elif args_str:
            contract_lines.append(f"[INPUT PARAMS]: {', '.join(args_str)}")

        # 2. Return Type Annotation & Detected Shapes
        ret_annotation = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        if ret_annotation:
            contract_lines.append(f"[RETURN TYPE HINT]:{ret_annotation}")
            
        if analyzer.response_out_keys:
            contract_lines.append(f"[HTTP RESPONSE KEYS]: {', '.join(sorted(analyzer.response_out_keys))}")
        elif analyzer.return_shapes:
            contract_lines.append(f"[RETURN SHAPES DETECTED]: {', '.join(sorted(analyzer.return_shapes))}")

        # 3. Side Effects & DB Operations
        if analyzer.db_ops:
            contract_lines.append(f"[DB OPS]: {', '.join(sorted(analyzer.db_ops))}")
        if analyzer.side_effects:
            contract_lines.append(f"[SIDE EFFECTS]: {', '.join(sorted(analyzer.side_effects))}")

        # Format Docstring Baru
        new_doc_parts = []
        if existing_doc:
            new_doc_parts.append(existing_doc.strip())
            if contract_lines:
                new_doc_parts.append("-" * 40)
        if contract_lines:
            new_doc_parts.extend(contract_lines)
            
        final_doc = "\n".join(new_doc_parts)
        
        # Kosongkan body fungsi, sisakan docstring + pass
        new_body = []
        if final_doc:
            new_body.append(ast.Expr(value=ast.Constant(value=final_doc)))
        new_body.append(ast.Pass())
        
        node.body = new_body
        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)


def process_python(content: str) -> str:
    try:
        tree = ast.parse(content)
        transformer = PythonRichTransformer()
        skeleton_tree = transformer.visit(tree)
        ast.fix_missing_locations(skeleton_tree)
        return ast.unparse(skeleton_tree)
    except Exception as e:
        return f"# [Error parsing Python AST: {e}]"

# ==========================================
# 2. RICH PARSER REACT / TS / JS
# ==========================================
def process_react(content: str) -> str:
    output_lines = []
    type_or_interface = re.compile(r'^\s*(export\s+)?(type|interface|enum)\s+')
    func_or_component = re.compile(
        r'^\s*(export\s+)?(default\s+)?(async\s+)?(function\s+\w+|const\s+\w+[\s:]*.*?=)'
    )
    
    in_interface_block = False
    brace_count = 0

    for line in content.splitlines():
        stripped = line.strip()
        
        # Simpan Imports
        if stripped.startswith("import ") and ("from" in stripped or ";" in stripped):
            output_lines.append(line)
            continue
            
        # Simpan Interface / Types / Enums secara utuh
        if type_or_interface.search(line) or in_interface_block:
            output_lines.append(line)
            brace_count += line.count('{') - line.count('}')
            in_interface_block = brace_count > 0
            continue
            
        # Ringkas Fungsi / Component tapi pertahankan Type Definition Parameter
        if func_or_component.search(line):
            if "=>" in line and "{" not in line:
                clean = re.sub(r'=>.*$', '=> { /* implementation */ }', line)
            elif "{" in line:
                clean = re.sub(r'\{[^{}]*$', '{ /* implementation */ }', line)
            else:
                clean = line + " { /* implementation */ }"
            output_lines.append(clean)
            
    return "\n".join(output_lines)

# ==========================================
# 3. CLI RUNNER
# ==========================================
def generate_skeleton_from_paths(targets: list[Path]) -> str:
    markdown_output = []
    files_to_process = []
    valid_exts = {'.py', '.js', '.jsx', '.ts', '.tsx'}

    for target in targets:
        if target.is_file():
            if target.suffix.lower() in valid_exts:
                files_to_process.append(target)
        elif target.is_dir():
            for root, _, files in os.walk(target):
                if any(ignore in root for ignore in ['venv', 'node_modules', '.git', '__pycache__', 'dist', 'build']):
                    continue
                for f in files:
                    if Path(f).suffix.lower() in valid_exts:
                        files_to_process.append(Path(root) / f)

    files_to_process = list(dict.fromkeys(files_to_process))

    for file_path in files_to_process:
        ext = file_path.suffix.lower()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                
            if ext == '.py':
                skeleton = process_python(code)
                lang_tag = 'python'
            else:
                skeleton = process_react(code)
                lang_tag = 'typescript' if ext in ['.ts', '.tsx'] else 'javascript'
                
            markdown_output.append(f"### File: `{file_path}`\n```{lang_tag}\n{skeleton}\n```\n")
        except Exception as e:
            markdown_output.append(f"### File: `{file_path}`\nError reading file: {e}\n")
            
    return "\n".join(markdown_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Rich Context Skeleton for AI Agents."
    )
    parser.add_argument(
        'targets', 
        metavar='TARGET', 
        type=Path, 
        nargs='+', 
        help='Satu atau beberapa file/folder target'
    )
    parser.add_argument(
        '-o', '--output', 
        type=Path, 
        default=Path('skeleton_context.md'), 
        help='Path file markdown output (default: skeleton_context.md)'
    )

    args = parser.parse_args()

    for t in args.targets:
        if not t.exists():
            print(f"Error: Target path '{t}' tidak ditemukan.")
            sys.exit(1)

    result = generate_skeleton_from_paths(args.targets)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(result)
        
    print(f"✅ Rich Skeleton Context berhasil diekstrak ke: {args.output.resolve()}")