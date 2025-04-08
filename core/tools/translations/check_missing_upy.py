from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
CORE = HERE.parent.parent
CORE_SRC = CORE / "src"
KEY_PREFIX = ""

MAPPING_FILE = HERE / "mapping_upy.json"
IGNORE_FILE = HERE / "ignore_upy.json"

if IGNORE_FILE.exists():
    content = json.loads(IGNORE_FILE.read_text())
    IGNORE_SET: set[str] = set(content.keys())
else:
    IGNORE_SET = set()  # type: ignore


def find_all_strings(filename: str | Path) -> list[str]:
    with open(filename, "r") as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    strings: list[str] = []

    class StringVisitor(ast.NodeVisitor):
        def visit_Str(self, node: ast.Str):
            strings.append(node.s)

        def visit_JoinedStr(self, node: ast.JoinedStr):
            for value in node.values:
                if isinstance(value, ast.Str):
                    strings.append(value.s)

    visitor = StringVisitor()
    visitor.visit(tree)

    return strings


def find_strings_to_ignore(filename: str | Path) -> list[str]:
    with open(filename, "r") as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    strings: list[str] = []

    def ignore_func(func_name: str) -> bool:
        if not func_name:
            return True
        substrs = ["Error", "Exception", "wire.", "log.", "ensure", "mem_trace"]
        if any(substr in func_name for substr in substrs):
            return True
        if func_name in (
            "_log",
            "info",
            "warning",
            "debug",
            "Success",
            "SdCardUnavailable",
            "NotInitialized",
            "ActionCancelled",
            "UnexpectedMessage",
            "NotEnoughFunds",
            "Failure",
            "PinCancelled",
            "TypeVar",
            "getattr",
            "_validate_public_key",
            "check_mem",
            "halt",
            "pack",
            "mem_trace",
        ):
            return True
        return False

    def get_final_attribute_name(node: ast.AST) -> str:
        """Recursively extracts the final attribute name from a nested attribute expression."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return get_final_attribute_name(node.value) + "." + node.attr
        return ""

    def include_all_strings(arg: ast.expr) -> None:
        if isinstance(arg, ast.Str):
            strings.append(arg.s)
        elif isinstance(arg, ast.JoinedStr):
            for value in arg.values:
                if isinstance(value, ast.Str):
                    strings.append(value.s)
                elif isinstance(value, ast.FormattedValue):
                    # This part is an expression inside an f-string
                    expr_as_str = ast.dump(value.value, annotate_fields=False)
                    strings.append(expr_as_str)

    class IgnoreStringVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            func_name = get_final_attribute_name(node.func)
            if ignore_func(func_name):
                for arg in node.args + [kw.value for kw in node.keywords]:
                    include_all_strings(arg)
            # Continue visiting the children of this node (!!!Necessary!!!)
            self.generic_visit(node)

        def visit_Assert(self, node: ast.Assert):
            error_message = node.msg
            if error_message:
                include_all_strings(error_message)
            self.generic_visit(node)

        def visit_Assign(self, node: ast.Assign):
            ignore_variables = [
                "msg_wire",
                "msg_type",
            ]
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ignore_variables:
                    value = node.value
                    include_all_strings(value)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef):
            for arg in node.args.args:
                annotation = arg.annotation
                if annotation:
                    include_all_strings(annotation)
            return_annotation = node.returns
            if return_annotation:
                include_all_strings(return_annotation)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
            for arg in node.args.args:
                annotation = arg.annotation
                if annotation:
                    include_all_strings(annotation)
            return_annotation = node.returns
            if return_annotation:
                include_all_strings(return_annotation)
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign):
            annotation = node.annotation
            include_all_strings(annotation)
            self.generic_visit(node)

    visitor = IgnoreStringVisitor()
    visitor.visit(tree)

    # get all the top-level string comments
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(
            node.value, (ast.Str, ast.JoinedStr)
        ):
            strings.append(node.value.s)  # type: ignore

    return strings


def find_docstrings(filename: str | Path) -> list[str]:
    with open(filename, "r") as file:
        file_content = file.read()

    tree = ast.parse(file_content)

    functions = [
        f
        for f in ast.walk(tree)
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    function_docs = [ast.get_docstring(f) for f in functions]

    classes = [c for c in ast.walk(tree) if isinstance(c, ast.ClassDef)]
    class_docs = [ast.get_docstring(c) for c in classes]

    all_docstrings = function_docs + class_docs

    module_docstring = ast.get_docstring(tree)
    if module_docstring:
        all_docstrings.append(module_docstring)

    return [doc for doc in all_docstrings if doc]


def check_file(file: str | Path) -> list[str]:
    all_strings = find_all_strings(file)

    def is_docstring(string: str) -> bool:
        return "\n " in string or (string.startswith("\n") and string.endswith("\n"))

    all_strings = [string for string in all_strings if not is_docstring(string)]
    ignore_strings = find_strings_to_ignore(file)
    docstrings = find_docstrings(file)

    # Remove duplicates
    all_strings = list(set(all_strings))
    ignore_strings = set(ignore_strings)
    docstrings = set(docstrings)

    to_ignore = ignore_strings | docstrings

    # Remove strings that are passed to error and other non-translatable functions
    return [s for s in all_strings if s not in to_ignore]


def check_file_report(file: str | Path) -> None:
    all_files = {str(file): check_file(file)}
    report_all_files(all_files)


def check_folder_resursive_report(
    folder: str | Path, ignore_files: list[str] | None = None
) -> None:
    if ignore_files is None:
        ignore_files = []
    all_files: dict[str, list[str]] = {}
    for file in Path(folder).rglob("*.py"):
        if file.name in ignore_files:
            continue
        file_strings = check_file(file)
        all_files[str(file)] = file_strings
    report_all_files(all_files)


def report_all_files(all_files: dict[str, list[str]]) -> None:
    str_mapping: dict[str, str] = {}
    for _file, strings in all_files.items():
        for string in strings:
            if "_" in string:
                continue
            str_id = (
                string.lower()
                .strip()
                .replace(" ", "_")
                .replace("-", "_")
                .replace(":", "")
                .replace("?", "")
            )
            if KEY_PREFIX:
                str_id = f"{KEY_PREFIX}__{str_id}"
            if str_id in IGNORE_SET:
                continue
            str_mapping[str_id] = string
    MAPPING_FILE.write_text(json.dumps(str_mapping, indent=4))


if __name__ == "__main__":
    ignore_files = [
        "coininfo.py",
        "nem_mosaics.py",
        "knownapps.py",
        "networks.py",
        "tokens.py",
        "workflow_handlers.py",
        "messages.py",
        "errors.py",
    ]

    # folder = CORE_SRC / "apps"
    # folder = CORE_SRC / "trezor"
    folder = CORE_SRC
    check_folder_resursive_report(folder, ignore_files=ignore_files)

    # file = CORE_SRC / "trezor/ui/layouts/tt_v2/reset.py"
    # KEY_PREFIX = "TR.reset"  # type: ignore
    # check_file_report(file)
