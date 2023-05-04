#!/usr/bin/env python3
"""
Compare the mock python API with the real Rust one.
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).parent
CORE_DIR = HERE.parent
TT_FILE = CORE_DIR / "embed/rust/src/ui/model_tt/layout.rs"
TR_FILE = CORE_DIR / "embed/rust/src/ui/model_tr/layout.rs"
ALL_FILES = [
    TT_FILE,
    TR_FILE,
]
# These are functions not defined directly in layout.rs
RUST_EXTERNAL_FUNCTIONS = [
    "disable_animation",
    "jpeg_info",
    "jpeg_test",
]
# These functions do not directly proccess upy arguments
RUST_DELEGATING_FUNCTIONS = [
    "new_show_success",
    "new_show_warning",
    "new_show_error",
    "new_show_info",
]


def _get_all_functions_with_definitions(file: Path) -> dict[str, str]:
    all_functions: dict[str, str] = {}

    with open(file, "r") as f:
        lines = f.readlines()

    func_name: str | None = None
    definition_lines: list[str] = []
    for line in lines:
        # Function name
        func_match = re.search(r'^extern "C" fn (\w+)', line)
        if func_match:
            func_name = func_match.group(1)
            continue

        if not func_name:
            continue

        # Saving the line
        definition_lines.append(line.rstrip())

        # End of definition - save and reset
        if line.startswith("}"):
            if func_name:
                all_functions[func_name] = "\n".join(definition_lines)
                func_name = None
                definition_lines = []
                continue

    return all_functions


def _get_all_qstr_code_types(file: Path) -> dict[str, dict[str, str]]:
    all_function_defs = _get_all_functions_with_definitions(file)

    all_qstr_defs: dict[str, dict[str, str]] = {}
    for func_name, func_def in all_function_defs.items():
        qstr_defs: dict[str, str] = {}
        one_separated_line: list[str] = []
        for line in func_def.splitlines():
            one_separated_line.append(line.strip())
            if not line.endswith(";"):
                continue
            one_line = "".join(one_separated_line)
            one_separated_line = []

            qstr_match = re.search(r"MP_QSTR_(\w+)", one_line)
            if not qstr_match:
                continue
            qstr_name = qstr_match.group(1)

            rust_match = re.search(r"let (\w+): (.*?) =", one_line)
            if not rust_match:
                raise ValueError("No Rust type found")
            rust_type = rust_match.group(2)

            if rust_type == "Obj":
                # Cannot get the exact type
                upy_type = "Any"
            else:
                upy_type = rust_type

            # There could be a default value
            default = None
            if "unwrap_or_else" in one_line:
                default_match = re.search(r"unwrap_or_else\(\|_\|\s+(.*?)\)", one_line)
                if default_match:
                    default = default_match.group(1)
                else:
                    raise ValueError("No default value found")
            elif "kwargs.get_or(" in one_line:
                default_match = re.search(
                    r"kwargs.get_or\(Qstr::MP_QSTR_\w+, (.*?)\)", one_line
                )
                if default_match:
                    default = default_match.group(1)
                else:
                    raise ValueError("No default value found")

            option_match = re.match(r"Option<(.*)>", upy_type)
            if option_match:
                upy_type = option_match.group(1)
                upy_type = f"{upy_type} | None"

            gc_match = re.match(r"Gc<(.*)>", upy_type)
            if gc_match:
                upy_type = gc_match.group(1)

            upy_type = upy_type.replace("StrBuffer", "str")
            upy_type = upy_type.replace("List", "list")
            if re.match(r"^[ui]\d+$", upy_type) or upy_type == "usize":
                upy_type = "int"

            if default:
                if "const_none" in default:
                    default = "None"
                elif default in ("true", "false"):
                    default = default.capitalize()
                elif ".into(" in default:
                    default = default.split(".into(")[0]
                elif "StrBuffer::empty" in default:
                    default = '""'

                upy_type += f" = {default}"

            qstr_defs[qstr_name] = upy_type

        all_qstr_defs[func_name] = qstr_defs

    return all_qstr_defs


def _get_all_upy_types(file: Path) -> dict[str, dict[str, str]]:
    all_functions: dict[str, dict[str, str]] = {}

    with open(file, "r") as f:
        lines = f.readlines()

    func_name: str | None = None
    definition_lines: list[str] = []
    for line in lines:
        line = line.strip()

        # Function name
        func_match = re.search(r"^/// def (\w+)\(", line)
        if func_match:
            func_name = func_match.group(1)
            continue

        if not func_name:
            continue

        # Saving the line
        definition_lines.append(line)

        # End of definition - save and reset
        if line.startswith("Qstr::MP_QSTR_"):
            if func_name:
                if f"new_{func_name}" in line:
                    func_name = f"new_{func_name}"
                def_text = "\n".join(definition_lines)
                var_names_and_types = re.findall(r"(\w+): ([^#]*?)[,\n]", def_text)
                all_functions[func_name] = {
                    name: type for name, type in var_names_and_types
                }
                unused_args: list[str] = []
                for def_l in definition_lines:
                    if "# unused" in def_l:
                        unused_match = re.search(r"(\w+):", def_l)
                        if unused_match:
                            unused_args.append(unused_match.group(1))
                all_functions[func_name]["_unused_args"] = unused_args  # type: ignore
                func_name = None
                definition_lines = []
                continue

    return all_functions


def check_file(file: Path) -> None:
    all_rust_types = _get_all_qstr_code_types(file)
    all_upy_types = _get_all_upy_types(file)

    # Find discrepancies between these types
    for func_name, rust_types in all_rust_types.items():
        upy_types = all_upy_types.get(func_name)
        if upy_types is None:
            print(f"Missing upy function {func_name}")
            continue
        unused_args = upy_types.get("_unused_args", [])
        for qstr_name, rust_type in rust_types.items():
            upy_type = upy_types.get(qstr_name)
            if not upy_type:
                print(f"Missing upy argument {qstr_name} in {func_name} ({rust_type})")
                continue
            if upy_type and qstr_name in unused_args:
                print(f"Argument {qstr_name} marked as unused but used in {func_name}")
            if rust_type != upy_type:
                if rust_type == "Any":
                    continue
                if rust_type == "list" and upy_type.startswith("list"):
                    continue
                print(f"Discrepancy in {func_name} {qstr_name}:")
                print(f"  Rust: {rust_type}")
                print(f"  Upy:  {upy_type}")

    # Find things missing in Rust
    for func_name, upy_types in all_upy_types.items():
        rust_types = all_rust_types.get(func_name)
        if rust_types is None:
            if func_name in RUST_EXTERNAL_FUNCTIONS:
                continue
            print(f"Missing Rust function {func_name}")
            continue
        unused_args = upy_types.get("_unused_args", [])
        for qstr_name, upy_type in upy_types.items():
            if qstr_name == "_unused_args":
                continue
            rust_type = rust_types.get(qstr_name)
            if not rust_type and qstr_name not in unused_args:
                if func_name in RUST_DELEGATING_FUNCTIONS:
                    continue
                print(f"Not parsing argument {qstr_name} in {func_name}")
                continue


def main() -> None:
    for file in ALL_FILES:
        print(f"Checking {file}")
        check_file(file)


if __name__ == "__main__":
    main()
