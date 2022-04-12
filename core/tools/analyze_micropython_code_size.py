"""
Getting information about how big are the micropython applications
and functions stored in flash.

Example usage:
>>> python size.py --statistics
- shows overall size of each application
>>> python size.py --app ethereum --lines
- shows each function for ethereum app, including line numbers
>>> python size.py --grep ethereum_sign_tx
- shows all functions from ethereum/sign_tx module
>>> python size.py --file-name ethereum/sign_typed_data.py --lines
- shows all functions from ethereum/sign_typed_data.py, including line numbers
>>> python size.py --no-processing
- shows the raw output from the nm command, just with calculated total size
"""

import atexit
import json
import os
import re
import subprocess
from functools import cache
from pathlib import Path
from typing import Callable, Dict, Set

import click

Results = Dict[str, int]

CURRENT_DIR = Path(__file__).resolve().parent
LINES_CACHE_FILE = CURRENT_DIR / "mp_line_numbers_cache.json"

# Makes sure the paths are relative to the `core` directory
print("changing directory to `core`")
os.chdir(CURRENT_DIR.parent)

BUILD_CMD = "make build_firmware"
BIN_TO_ANALYZE = "build/firmware/frozen_mpy.o"

NM_CMD_BASE = f"nm --radix=dec --size-sort {BIN_TO_ANALYZE}"


@click.command()
@click.option("-a", "--app", help="App which to analyze - e.g. `ethereum`")
@click.option("-b", "--build", is_flag=True, help="Perform build")
@click.option(
    "-g", "--grep", help="Custom string to filter with - e.g. `bitcoin_common`"
)
@click.option(
    "-f", "--file-name", help="Check only specific file - e.g. `ethereum/networks.py`"
)
@click.option(
    "-s", "--statistics", is_flag=True, help="Overall statistics for all apps"
)
@click.option(
    "-l", "--lines", is_flag=True, help="Get line definitions for all functions"
)
@click.option(
    "-p", "--no-processing", is_flag=True, help="Do not process the function names"
)
def main(
    app: str,
    build: bool,
    grep: str,
    file_name: str,
    statistics: bool,
    lines: bool,
    no_processing: bool,
) -> None:
    cmd = NM_CMD_BASE
    if app is not None:
        cmd = f"{cmd} | grep -i apps_{app}"
    if grep is not None:
        cmd = f"{cmd} | grep -i {grep}"

    if build:
        build_binary()

    # Get output from nm command
    nm_result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, shell=True)

    if nm_result.returncode != 0:
        print(f"Error while running `{cmd}` - see above")
        exit(1)

    # Parse output for useful results (extract the size of each function/object)
    current_results: Results = get_results(
        nm_result.stdout, processing=not no_processing, lines=lines
    )

    # Filter the results for the exact file name
    # TODO: could be included in get_results(), not having to process all the results
    if file_name:
        current_results = {k: v for k, v in current_results.items() if file_name in k}

    if statistics:
        print_statistics(current_results)
    else:
        # Calculate total size and amount
        current_results["total"] = sum(current_results.values())
        current_results["total_amount"] = len(current_results) - 1  # -1 for total

        # Print into terminal
        print_results(current_results, align=bool(file_name))
        print(f"{cmd=}")


def print_statistics(current_results: Results) -> None:
    """Prints the statistics for all the apps"""
    # Take only "src/" files
    all_modules: Set[str] = set()
    for module in current_results:
        module_name = module.split()[0]
        if module_name.startswith("src/"):
            all_modules.add(module_name[len("src/") :])

    # Getting all files/directories from src/ maximum two levels deep
    two_level_modules: Set[str] = set()
    for module in all_modules:
        parts = module.split("/")
        if len(parts) >= 2:
            two_level_modules.add(f"{parts[0]}/{parts[1]}")
        elif len(parts) == 1:
            two_level_modules.add(f"{parts[0]}")

    # Gather results for each module/file
    overall_results: Results = {}
    for module in two_level_modules:
        results = {k: v for k, v in current_results.items() if module in k}
        overall_results[module] = sum(results.values())

    # Print results
    overall_results["total"] = sum(overall_results.values())
    for func, size in sorted(overall_results.items(), key=lambda x: x[1]):
        print(f"{size:_}: {func}")


def get_results(stdout: str, processing: bool, lines: bool) -> Results:
    current_results: Results = {}

    for line in stdout.splitlines():
        size = int(line.split()[0])
        func_name = line.split()[-1]

        if processing:
            func_name = process_func_name(func_name, lines)

        # After processing, the function name might already be there, so deduplicate
        while func_name in current_results:
            func_name = f"{func_name} (1)"
        current_results[func_name] = size

    return current_results


def process_func_name(func_name: str, get_lines: bool) -> str:
    """Process function name to make it more clear"""
    # There are some unusual things that cannot be parsed properly
    if func_name.startswith(("mp_", "__compound_literal")):
        return func_name

    # Strip the common beginning
    prefix = "fun_data_"
    if func_name.startswith(prefix):
        func_name = func_name[len(prefix) :]

    # Splitting between module and function, if both exist
    if "__lt_module_gt__" in func_name:
        module_name, func_name = func_name.split("__lt_module_gt__", maxsplit=1)
    else:
        module_name = func_name.replace("__lt_module_gt_", "")  # stuff at the end
        func_name = ""

    # Extracting special identifier
    special_info = ""
    special_prefixes = ["const_table_data_", "const_obj_", "raw_code_"]
    for prefix in special_prefixes:
        if module_name.startswith(prefix):
            module_name = module_name[len(prefix) :]
            special_info = f"{prefix.upper().rstrip('_')} (SPECIAL)"
            break

    module_name = resolve_module(module_name)

    # Deleting strange suffixes that are only at the end (for example "__lt_genexpr_gt_")
    # TODO: create a general logix to look for "_gt_" and then remove all after rightmost "__"
    for strange_suffix in ("__lt_genexpr_gt_", "__lt_listcomp_gt_", "__lt_lambda_gt_"):
        func_name = func_name.replace(strange_suffix, "")

    # SomeClass_some_function -> SomeClass.some_function
    if func_name and func_name[0].isupper():
        func_name = func_name.replace("_", ".", 1)

    # Showing the exact line where the function is defined
    if get_lines and func_name:
        line_num = get_line_num(func_name, module_name)
        if line_num:
            module_name = f"{module_name}:{line_num}"

    module_func_part = f"{module_name} ... {func_name}" if func_name else module_name

    if special_info:
        return f"{module_func_part} - {special_info}"
    else:
        return module_func_part


@cache
def resolve_module(module_name: str) -> str:
    """Completing module and making a file-path structure"""
    module_name = f"{module_name}.py"

    # __init__.py is a special case
    if module_name.endswith("__init__.py"):
        module_parts = module_name[: -len("__init__.py")].split("_") + ["__init__.py"]
    else:
        module_parts = module_name.split("_")

    # Gradually filling the filename (generally replacing "_" with "/")
    # As some modules can themselves contain "_", we need to check if they exist
    # TODO: does not work for src/apps/monero/xmr, where both "serialize" and "serialize_message"
    # are both valid directories
    file_path = "src"
    for part in module_parts:
        if not part:
            continue

        if file_path.endswith("_"):
            possible_path = Path(f"{file_path}{part}")
        else:
            possible_path = Path(f"{file_path}/{part}")

        if possible_path.exists():
            file_path = str(possible_path)
        else:
            file_path = f"{possible_path}_"

    return file_path


def get_line_num(func_name: str, module_name: str) -> str:
    # Sometimes functions have strange number suffix not defined in the function name
    func_name = re.sub(r"_\d+$", "", func_name)

    # There may be a class, so point at it, also in case of __init__,
    # which would be harder to find exactly for specific class
    class_name = ""
    if "." in func_name:
        cls, func_name = func_name.split(".", maxsplit=1)
        if func_name == "__init__":
            class_name = cls
    elif func_name[0].isupper():
        class_name = func_name

    to_search = f"class {class_name}[(:]" if class_name else f"def {func_name}("
    cmd = f'grep -m1 -n0 "{to_search}" {module_name} | cut -d: -f1'
    return get_line_num_grep(cmd)


def file_cache(
    file_name: str,
) -> Callable[[Callable[[str], str]], Callable[[str], str]]:
    """Decorator to cache the results of a function to a file"""
    try:
        cache: Dict[str, str] = json.load(open(file_name, "r"))
    except (IOError, ValueError):
        cache = {}

    atexit.register(lambda: json.dump(cache, open(file_name, "w"), indent=4))

    def decorator(func: Callable[[str], str]) -> Callable[[str], str]:
        def new_func(param: str) -> str:
            if param not in cache:
                cache[param] = func(param)
            return cache[param]

        return new_func

    return decorator


# Cached on disk because it can take a long time to get lines for all functions
@file_cache(LINES_CACHE_FILE)
def get_line_num_grep(cmd: str) -> str:
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, text=True, shell=True
    ).stdout.strip()
    # Make sure it has always three spaces, to align the same files nicely
    while len(result) < 3:
        result = result + " "
    return result


def print_results(current_results: Results, align: bool = False) -> None:
    for func, size in current_results.items():
        if align:
            # Aligning the size to take 3 spaces to show filename always vertically
            buff = ""
            diff = 3 - len(str(size))
            if diff > 0:
                buff = diff * " "

            print(f"{size}:{buff} {func}")
        else:
            print(f"{size}: {func}")


def build_binary() -> None:
    print(f"building the binary... `{BUILD_CMD}`")
    build_result = subprocess.run(
        BUILD_CMD, stdout=subprocess.PIPE, text=True, shell=True
    )
    if build_result.returncode != 0:
        print("build failed")
        exit(1)


if "__main__" == __name__:
    main()
