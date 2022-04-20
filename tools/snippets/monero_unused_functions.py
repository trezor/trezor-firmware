"""
Find out which functions are unused in the Monero app - based on
`monero.pyi` file.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent.parent

HELPER_FILE = ROOT_DIR / "core/src/apps/monero/xmr/crypto_helpers.py"
MOCK_FILE = ROOT_DIR / "core/mocks/generated/trezorcrypto/monero.pyi"


def generate_function_mapping() -> Dict[str, List[str]]:
    """Look at all Monero functions and generate a mapping of their usage"""

    # Load all the function names in .pyi file
    pyi_functions: Set[str] = set()
    with open(MOCK_FILE, "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("def"):
                f_name = line.split("(")[0].split(" ")[1]
                pyi_functions.add(f_name)

    # Load definitions of helper functions
    helper_func_defs: Dict[str, str] = {}
    with open(HELPER_FILE, "r") as f:
        lines = f.readlines()
        current_func = ""
        for line in lines:
            if line.startswith("def"):
                current_func = line.split("(")[0].split(" ")[1]
                helper_func_defs[current_func] = line
            elif not current_func:
                continue
            else:
                helper_func_defs[current_func] += line

    # Try to connect function names with helper definitions
    func_mapping: Dict[str, List[str]] = {}
    for func_name in pyi_functions:
        func_mapping[func_name] = []
        for func_def_name, func_code in helper_func_defs.items():
            if f".{func_name}(" in func_code:
                func_mapping[func_name].append(func_def_name)

        # Functions may not be used in helper file, alias them to themselves
        if not func_mapping[func_name]:
            func_mapping[func_name] = [func_name]

    return func_mapping


def check_usage_of_functions(func_mapping: Dict[str, List[str]]) -> None:
    """Go through all the functions and check if they are used in the Monero app.

    Generates a report and exits with an appropriate exit code.
    """

    # Include boolean field to know what is used
    is_used_mappings: Dict[str, Dict[str, Any]] = {}
    for func_name, mapping in func_mapping.items():
        is_used_mappings[func_name] = {"mapping": mapping, "is_used": False}

    # Check if any of the mapping names is used - and mark it as used if so
    for func_name in is_used_mappings:
        for mapping in is_used_mappings[func_name]["mapping"]:
            is_there = _is_used(mapping)
            if is_there:
                is_used_mappings[func_name]["is_used"] = True
                break

    # Find unused functions and generate a report
    unused_functions = {
        fc: val for fc, val in is_used_mappings.items() if not val["is_used"]
    }
    if not unused_functions:
        print("SUCCESS: no functions are unused")
        sys.exit(0)
    else:
        print(f"{len(unused_functions)} unused functions:")
        for func, values in unused_functions.items():
            print(func, values)
        sys.exit(1)


def _is_used(func_name: str) -> bool:
    """Find function usage in the Monero app or in test files"""

    cmds = [
        rf'grep -r ".{func_name}\b" {ROOT_DIR}/core/src/apps/monero',
        rf'grep -r ".{func_name}\b" {ROOT_DIR}/core/tests',
    ]

    for cmd in cmds:
        grep_result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        if grep_result.returncode == 0:
            return True

    return False


if "__main__" == __name__:
    func_mapping = generate_function_mapping()
    check_usage_of_functions(func_mapping)
