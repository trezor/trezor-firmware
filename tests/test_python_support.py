#!/usr/bin/env python3
"""
Verifying that all the tools can be run even by older python versions.

Uses `pyright --pythonversion 3.X <path>` output to check for substrings that
indicate the type-hints in the code are not compatible with this version.
"""

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT_DIR = HERE.parent

EXIT_CODE = 0

os.chdir(ROOT_DIR)

versions_to_check = [
    "3.7",
    "3.8",
    "3.9",
]

dirs_to_check = [
    "tools",
    "common",
    "core/tools",
]

signs_of_issues = [
    "is unknown import symbol",  # we need to import some stuff from typing_extensions instead of typing
    "will generate runtime exception",  # happens when using `dict` or `list` as a type alias
]


def check_directory(path: str, python_version: str) -> None:
    global EXIT_CODE
    cmd = (
        "pyright",
        "--pythonversion",
        python_version,
        path,
    )

    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    for line in result.stdout.splitlines():
        if any(sign in line for sign in signs_of_issues):
            print(line)
            EXIT_CODE = 1


for version in versions_to_check:
    print(f"Checking python version {version}")
    for dir_to_check in dirs_to_check:
        check_directory(dir_to_check, version)

sys.exit(EXIT_CODE)
