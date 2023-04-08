#!/usr/bin/env python3
"""
Check the consistency of the Rust API between models.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CORE_DIR = HERE.parent
MOCK_FILE = CORE_DIR / "mocks/generated/trezorui2.pyi"


def _get_all_functions_with_definitions() -> dict[str, dict[str, str]]:
    all_functions: dict[str, dict[str, str]] = defaultdict(dict)

    with open(MOCK_FILE, "r") as f:
        lines = f.readlines()

    model: str | None = None
    func_name: str | None = None
    definition_lines: list[str] = []
    for line in lines:
        # Model line, e.g. "# rust/src/ui/model_tt/layout.rs"
        model_match = re.search(r"^# rust/src/ui/model_(\w+)/", line)
        if model_match:
            model = model_match.group(1).upper()
            continue

        if model is None:
            continue

        # Function name
        func_match = re.search(r"^def\s+(\w+)", line)
        if func_match:
            func_name = func_match.group(1)

        # Getting rid of comments before saving the definition
        line = line.split("#")[0].rstrip()
        definition_lines.append(line)

        # End of definition - save and reset
        if line.endswith(":"):
            if func_name and model:
                all_functions[func_name][model] = "\n".join(definition_lines)
                func_name = None
                model = None
                definition_lines = []
                continue

    return all_functions


def main() -> None:
    all_functions = _get_all_functions_with_definitions()

    # Show only those in one model
    print(f"{40 * '/'}\nONLY ONE MODEL FUNCTIONS\n{40 * '/'}\n")
    only_one_model_amount = 0
    for func_name, func_defs in all_functions.items():
        if len(func_defs) == 1:
            print(f"{list(func_defs.keys())[0]} - {func_name}")
            only_one_model_amount += 1

    # Show those in both models, with comparing the definitions
    print(f"\n{40 * '/'}\nDIFFERENT IMPLEMENTATIONS\n{40 * '/'}\n")
    diff_impl_amount = 0
    for func_name, func_defs in all_functions.items():
        if len(func_defs) == 2:
            models = list(func_defs.keys())
            if func_defs[models[0]] != func_defs[models[1]]:
                print(func_name)
                for model in func_defs.keys():
                    print(model + " - " + func_defs[model])
                print("\n" + "-" * 40 + "\n")
                diff_impl_amount += 1

    print(f"Total only one model functions: {only_one_model_amount}")
    print(f"Total different implementations: {diff_impl_amount}")


if __name__ == "__main__":
    main()
