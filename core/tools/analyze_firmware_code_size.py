"""
Getting information about how big are the functions in the binary.

Specifically created for Rust functions, but can be controlled by MODE variable
to show even overall functions/pieces of binary.

Allows for experimentation as it tracks the previous result
(and also the original "benchmark" result), so one can modify the
source code, build the binary (or use the --build option) and
see how the size increased/decreased.

See all the script options with `--help` flag.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict

import click

CURRENT_DIR = Path(__file__).resolve().parent
LATEST_RESULTS_FILE = CURRENT_DIR / "fw_size_profiling_latest.json"
BENCHMARK_FILE = CURRENT_DIR / "fw_size_profiling_benchmark.json"

# Makes sure the paths are relative to the `core` directory
print("changing directory to `core`")
os.chdir(CURRENT_DIR.parent)

BUILD_CMD = "make build_unix"
# BIN_TO_ANALYZE = "build/unix/trezor-emu-core"
BIN_TO_ANALYZE = "build/firmware/firmware.elf"

NM_CMD_BASE = f"nm --radix=dec --size-sort {BIN_TO_ANALYZE}"

# Describing what we are looking for
MODES_CMDS = {
    "all": NM_CMD_BASE,
    "rust_all": f"{NM_CMD_BASE} | grep -i trezor_lib",
    "rust_ui": f"{NM_CMD_BASE} | grep -i trezor_lib | grep ui",
    "storagedevice": f"{NM_CMD_BASE} | grep -i storagedevice",
}


# Did not want to import termcolor
class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


@click.command()
@click.option("-m", "--mode", type=click.Choice(list(MODES_CMDS.keys())), default="all")
@click.option("-b", "--build", is_flag=True, help="Perform build")
@click.option(
    "-r",
    "--raw",
    is_flag=True,
    help="Just forward the nm results, no comparing/processing",
)
@click.option(
    "-s", "--save-benchmark", is_flag=True, help="Save current results as benchmark"
)
@click.option(
    "-n", "--no-benchmark", is_flag=True, help="Do not show benchmark comparison"
)
@click.option(
    "-p", "--no-processing", is_flag=True, help="Do not process the function names"
)
@click.option(
    "-c", "--no-compare", is_flag=True, help="Do not compare against other results"
)
def main(
    mode: str,
    build: bool,
    raw: bool,
    save_benchmark: bool,
    no_benchmark: bool,
    no_processing: bool,
    no_compare: bool,
) -> None:
    if raw:
        no_compare = True
        no_processing = True

    if build:
        build_binary()

    # Get output from nm command
    nm_result = subprocess.run(
        MODES_CMDS[mode], stdout=subprocess.PIPE, text=True, shell=True
    )

    if nm_result.returncode != 0:
        print(f"Error while running `{MODES_CMDS[mode]}` - see above")
        exit(1)

    # Parse output for useful results (extract the size of each function/object)
    current_results: Dict[str, int] = get_results(
        nm_result.stdout, processing=not no_processing
    )

    # Load previous results to compare with, if wanted
    if no_compare:
        benchmark_results = {}
        previous_results = {}
    else:
        if no_benchmark:
            benchmark_results = {}
        else:
            benchmark_results = load_from_json(BENCHMARK_FILE)
        previous_results = load_from_json(LATEST_RESULTS_FILE)

    # Account for deleted functions
    for func in benchmark_results:
        if func not in current_results:
            current_results[func] = 0

    # Calculate total size and amount
    current_results["total"] = sum(current_results.values())
    current_results["total_amount"] = len(current_results) - 1  # -1 for total

    # Print into terminal
    print_results(benchmark_results, previous_results, current_results)
    print(f"{mode=}, cmd='{MODES_CMDS[mode]}'")

    # Save final results and also benchmark if not there already
    save_into_json(LATEST_RESULTS_FILE, current_results)
    if save_benchmark or not benchmark_results:
        save_into_json(BENCHMARK_FILE, current_results)


def get_results(stdout: str, processing: bool) -> Dict[str, int]:
    current_results: Dict[str, int] = {}

    for line in stdout.splitlines():
        size = int(line.split()[0])
        func_name = line.split()[-1]

        # processing is only valid for rust functions
        if processing and "trezor_lib" in func_name:
            func_name = process_func_name(func_name, current_results)

        current_results[func_name] = size

    return current_results


def process_func_name(func_name: str, current_results: Dict[str, int]) -> str:
    """Process function name to remove prefix and suffix"""
    func_name = get_rid_of_prefix_and_suffix(func_name)

    def replace_but_not_39(value: str, replace_value: str) -> str:
        """Not to break slip39"""
        return value if value == "39" else replace_value

    # nm output somehow uses digits to delimit module/function names
    func_name = re.sub(
        r"\d+", lambda m: replace_but_not_39(m.group(0), " :: "), func_name
    )
    func_name = func_name.strip(" :")

    # There could be possible duplicates after stripping the nonimporatnt parts
    while func_name in current_results:
        func_name = f"{func_name} (1)"

    return func_name


def get_rid_of_prefix_and_suffix(func_name: str) -> str:
    # Strip the possible beginning
    prefix = "_ZN10trezor_lib"
    if func_name.startswith(prefix):
        func_name = func_name[len(prefix) :]

    # Check if end contains expected hex (apart from "h") and strip it if so
    suffix_len = len("17hcb851c2b24315af0E")
    try:
        int(func_name[-suffix_len:].lower().replace("h", "f"), 16)
        return func_name[:-suffix_len]
    except ValueError:
        return func_name


def save_into_json(file: Path, results: Dict[str, int]) -> None:
    with open(file, "w") as f:
        json.dump(results, f, indent=4)


def load_from_json(file: Path) -> Dict[str, int]:
    if not file.exists():
        return {}

    with open(file, "r") as f:
        return json.load(f)


def print_results(
    benchmark_results: Dict[str, int],
    previous_results: Dict[str, int],
    current_results: Dict[str, int],
) -> None:
    for func, size in current_results.items():
        # Not comparing anything if nothing to compare with
        if not benchmark_results and not previous_results:
            print(f"{size}: {func}")
            continue

        # Calculate difference with benchmark, if it is nonempty
        if not benchmark_results:
            benchmark_diff_str = ""
        else:
            benchmark_size_diff = size - benchmark_results.get(func, 0)
            if benchmark_size_diff > 0:
                benchmark_diff_str = f" {bcolors.FAIL}{bcolors.BOLD}(+{benchmark_size_diff} bench){bcolors.ENDC}"
            elif benchmark_size_diff < 0:
                benchmark_diff_str = f" {bcolors.OKGREEN}{bcolors.BOLD}({benchmark_size_diff} bench){bcolors.ENDC}"
            else:
                benchmark_diff_str = ""

        # Calculate difference with previous results and print all
        previous_size = previous_results.get(func, 0)
        if size > previous_size:
            print(
                f"{bcolors.FAIL}{size} (+{size - previous_size}){benchmark_diff_str}: {func}{bcolors.ENDC}"
            )
        elif size < previous_size:
            print(
                f"{bcolors.OKGREEN}{size} (-{previous_size - size}){benchmark_diff_str}: {func}{bcolors.ENDC}"
            )
        else:
            print(f"{size}{benchmark_diff_str}: {func}")


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
