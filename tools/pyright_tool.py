#!/usr/bin/env python3
"""
Wrapper around pyright type checking to allow for easy ignore of specific error messages.
Thanks to it the `# type: ignore` does not affect the whole line,
so other problems at the same line cannot be masked by it.

Features:
- ignores specific pyright errors based on substring or regex
- reports empty `# type: ignore`s (without ignore reason in `[]`)
- reports unused `# type: ignore`s (for example after pyright is updated)
- allows for ignoring some errors in the whole file - see `FILE_SPECIFIC_IGNORES` variable
- allows for error aliases - see `ALIASES` variable

Usage:
- there are multiple options how to ignore/silence a pyright error:
    1 - "# type: ignore [<error_substring>]"
        - put it as a comment to the line we want to ignore
        - "# type: ignore [<error1>;;<error2>;;...]" if there are more than one errors on that line
        - also regex patterns are valid substrings
    2 - "# pyright: off" / "# pyright: on"
        - all errors in block of code between these marks will be ignored
    3 - FILE_SPECIFIC_IGNORES
        - ignore specific rules (defined by pyright) or error substrings in the whole file
    4 - ALIASES
        - create an alias for a common error and use is with option 1 - "# type: ignore [<error_alias>]"

Running the script:
- see all script argument by calling `python pyright_tool.py --help`
- only directories with existing `pyrightconfig.json` can be tested - see `--dir` flag

Simplified program flow (as it happens in PyrightTool.run()):
- extract and validate pyright config data from pyrightconfig.json
- collect all the pyright errors by actually running the pyright itself
- extract type-ignore information for all the files pyright was analyzing
- loop through all the pyright errors and try to match them against all the type-ignore rules
- if there are some unmatched errors, report them and exit with nonzero value
- also report unused ignores and other inconsistencies
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, TypedDict


class RangeDetail(TypedDict):
    line: int
    character: int


class Range(TypedDict):
    start: RangeDetail
    end: RangeDetail


class Error(TypedDict):
    file: str
    severity: str
    message: str
    range: Range
    rule: str


Errors = list[Error]


class Summary(TypedDict):
    filesAnalyzed: int
    errorCount: int
    warningCount: int
    informationCount: int
    timeInSec: float


class PyrightResults(TypedDict):
    version: str
    time: str
    generalDiagnostics: Errors
    summary: Summary


@dataclass
class IgnoreStatement:
    substring: str
    already_used: bool = False


@dataclass
class LineIgnore:
    line_no: int
    ignore_statements: list[IgnoreStatement]


LineIgnores = list[LineIgnore]
FileIgnores = dict[str, LineIgnores]


@dataclass
class FileSpecificIgnore:
    rule: str = ""
    substring: str = ""
    already_used: bool = False

    def __post_init__(self) -> None:
        if self.rule and self.substring:
            raise ValueError("Only one of rule|substring should be set")


FileSpecificIgnores = dict[str, list[FileSpecificIgnore]]


@dataclass
class PyrightOffIgnore:
    start_line: int
    end_line: int
    already_used: bool = False


PyrightOffIgnores = list[PyrightOffIgnore]
FilePyrightOffIgnores = dict[str, PyrightOffIgnores]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--dev", action="store_true", help="Creating the error file and not deleting it"
)
parser.add_argument(
    "--test",
    action="store_true",
    help="Reusing existing error file and not deleting it",
)
parser.add_argument("--log", action="store_true", help="Log details")
parser.add_argument(
    "--dir",
    help="Directory which to test, relative to the repository root. When empty, taking the directory of this file.",
    default="",
)
args = parser.parse_args()

if args.dev:
    should_generate_error_file = True
    should_delete_error_file = False
    print("Running in dev mode, creating the file and not deleting it")
elif args.test:
    should_generate_error_file = False
    should_delete_error_file = False
    print("Running in test mode, will reuse existing error file")
else:
    should_generate_error_file = True
    should_delete_error_file = True

SHOULD_GENERATE_ERROR_FILE = should_generate_error_file
SHOULD_DELETE_ERROR_FILE = should_delete_error_file
SHOULD_LOG = args.log

if args.dir:
    # Need to change the os directory to find all the files correctly
    # Repository root + the wanted directory.
    HERE = Path(__file__).resolve().parent.parent / args.dir
    if not HERE.is_dir():
        raise RuntimeError(f"Could not find directory {args.dir} under {HERE}")
    os.chdir(HERE)
else:
    # Directory of this file
    HERE = Path(__file__).resolve().parent

# TODO: move into a JSON or other config file
# Files need to have a relative location to the directory being tested
# Example (when checking `python` directory):
# "tools/helloworld.py": [
#     FileSpecificIgnore(rule="reportMissingParameterType"),
#     FileSpecificIgnore(substring="cannot be assigned to parameter"),
# ],
FILE_SPECIFIC_IGNORES: FileSpecificIgnores = {}


# Allowing for more readable ignore of common problems, with an easy-to-understand alias
ALIASES: dict[str, str] = {
    "awaitable-is-generator": 'Return type of generator function must be "Generator" or "Iterable"',
    "obscured-by-same-name": "is obscured by a declaration of the same name",
    "int-into-enum": 'Expression of type "int.*" cannot be assigned to return type ".*"',
}


class PyrightTool:
    ON_PATTERN: Final = "# pyright: on"
    OFF_PATTERN: Final = "# pyright: off"
    IGNORE_PATTERN: Final = "# type: ignore"
    IGNORE_DELIMITER: Final = ";;"

    original_pyright_results: PyrightResults
    all_files_to_check: set[str]
    all_pyright_ignores: FileIgnores
    pyright_off_ignores: FilePyrightOffIgnores
    real_errors: Errors
    unused_ignores: list[str]
    inconsistencies: list[str] = []

    def __init__(
        self,
        pyright_config_file: str | Path,
        *,
        file_specific_ignores: FileSpecificIgnores | None = None,
        aliases: dict[str, str] | None = None,
        error_file: str | Path = "temp_error_file.json",
        should_generate_error_file: bool = True,
        should_delete_error_file: bool = True,
        should_log: bool = False,
    ) -> None:
        self.pyright_config_file = pyright_config_file
        self.file_specific_ignores = file_specific_ignores or {}
        self.aliases = aliases or {}
        self.error_file = error_file
        self.should_generate_error_file = should_generate_error_file
        self.should_delete_error_file = should_delete_error_file
        self.should_log = should_log

        self.count_of_ignored_errors = 0

        self.check_input_correctness()

    def check_input_correctness(self) -> None:
        """Verify the input data structures are correct."""
        # Checking for correct file_specific_ignores structure
        for file, ignores in self.file_specific_ignores.items():
            for ignore in ignores:
                if not isinstance(ignore, FileSpecificIgnore):
                    raise RuntimeError(
                        "All items of file_specific_ignores must be FileSpecificIgnore classes. "
                        f"Got {ignore} - type {type(ignore)}"
                    )
            # Also putting substrings at the beginning of ignore-lists, so they are matched before rules
            # (Not to leave them potentially unused when error would be matched by a rule instead)
            self.file_specific_ignores[file].sort(
                key=lambda x: x.substring, reverse=True
            )

        # Checking for correct aliases (dict[str, str] type)
        for alias, full_substring in self.aliases.items():
            if not isinstance(alias, str) or not isinstance(full_substring, str):
                raise RuntimeError(
                    "All alias keys and values must be strings. "
                    f"Got {alias} (type {type(alias)}), {full_substring} (type {type(full_substring)}"
                )

    def run(self) -> None:
        """Main function, putting together all logic and evaluating result."""
        self.pyright_config_data = self.get_and_validate_pyright_config_data()

        self.original_pyright_results = self.get_original_pyright_results()

        self.all_files_to_check = self.get_all_files_to_check()
        self.all_pyright_ignores = self.get_all_pyright_ignores()
        self.pyright_off_ignores = self.get_pyright_off_ignores()

        self.real_errors = self.get_all_real_errors()
        self.unused_ignores = self.get_unused_ignores()

        self.evaluate_final_result()

    def evaluate_final_result(self) -> None:
        """Reporting results to the user/CI (printing stuff, deciding exit value)."""
        print(
            f"\nIgnored {self.count_of_ignored_errors} custom-defined errors "
            f"from {len(self.all_pyright_ignores)} files."
        )

        if self.unused_ignores:
            print("\nWARNING: there are unused ignores!")
            for unused_ignore in self.unused_ignores:
                print(unused_ignore)

        if self.inconsistencies:
            print("\nWARNING: there are inconsistencies!")
            for inconsistency in self.inconsistencies:
                print(inconsistency)

        if not self.real_errors:
            print("\nSUCCESS: Everything is fine!")
            if self.unused_ignores or self.inconsistencies:
                print("But we have unused ignores or inconsistencies!")
                sys.exit(2)
            else:
                sys.exit(0)
        else:
            print("\nERROR: We have issues!\n")
            for error in self.real_errors:
                print(self.get_human_readable_error_string(error))
            print(f"Found {len(self.real_errors)} issues above")
            if self.unused_ignores or self.inconsistencies:
                print("And we have unused ignores or inconsistencies!")
            sys.exit(1)

    def get_and_validate_pyright_config_data(self) -> dict[str, Any]:
        """Verify that pyrightconfig exists and has correct data."""
        if not os.path.isfile(self.pyright_config_file):
            raise RuntimeError(
                f"Pyright config file under {self.pyright_config_file} does not exist! "
                "Tool relies on its existence, please create it."
            )

        try:
            config_data = json.loads(open(self.pyright_config_file, "r").read())
        except json.decoder.JSONDecodeError as err:
            raise RuntimeError(
                f"Pyright config under {self.pyright_config_file} does not contain valid JSON! Err: {err}"
            ) from None

        # enableTypeIgnoreComments MUST be set to False, otherwise the "type: ignore"s
        # will affect the original pyright result - and we need it to grab all the errors
        # so we can handle them on our own
        if (
            "enableTypeIgnoreComments" not in config_data
            or config_data["enableTypeIgnoreComments"]
        ):
            raise RuntimeError(
                f"Please set '\"enableTypeIgnoreComments\": true' in {self.pyright_config_file}. "
                "Otherwise the tool will not work as expected."
            )

        return config_data

    def get_original_pyright_results(self) -> PyrightResults:
        """Extract all information from pyright.

        `pyright --outputjson` will return all the results in
        nice JSON format with `generalDiagnostics` array storing
        all the errors - schema described in PyrightResults
        """
        if self.should_generate_error_file:
            cmd = f"pyright -p {self.pyright_config_file} --outputjson > {self.error_file}"
            exit_code = subprocess.call(cmd, shell=True)
            # Checking if there was no non-type-checking error when running the above command
            # Exit code 0 = all fine, no type-checking issues in pyright
            # Exit code 1 = pyright has found some type-checking issues (expected)
            # All other exit codes mean something non-type-related got wrong (or pyright was not found)
            # https://github.com/microsoft/pyright/blob/main/docs/command-line.md#pyright-exit-codes
            if exit_code not in (0, 1):
                raise RuntimeError(
                    f"Running '{cmd}' produced a non-expected exit code (see output above)."
                )

            if not os.path.isfile(self.error_file):
                raise RuntimeError(
                    f"Pyright error file under {self.error_file} was not generated by running '{cmd}'."
                )

        try:
            pyright_results: PyrightResults = json.loads(
                open(self.error_file, "r").read()
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Error file under {self.error_file} does not exist!"
            ) from None
        except json.decoder.JSONDecodeError as err:
            raise RuntimeError(
                f"Error file under {self.error_file} does not contain valid JSON! Err: {err}"
            ) from None

        if self.should_delete_error_file:
            os.remove(self.error_file)

        return pyright_results

    def get_all_real_errors(self) -> Errors:
        """Analyze all pyright errors and discard all that should be ignored.

        Ignores can be different:
        - as per "# type: ignore [<error_substring>]" comment
        - as per "file_specific_ignores"
        - as per "# pyright: off" mark
        """
        real_errors: Errors = []
        for error in self.original_pyright_results["generalDiagnostics"]:
            # Special handling of cycle import issues, which have different format
            if "range" not in error:
                error["range"] = {"start": {"line": 0}}
                error["rule"] = "cycleImport"
                real_errors.append(error)
                continue

            file_path = error["file"]
            error_message = error["message"]
            line_no = error["range"]["start"]["line"]

            # Checking for "# type: ignore [<error_substring>]" comment
            if self.should_ignore_per_inline_substring(
                file_path, error_message, line_no
            ):
                self.count_of_ignored_errors += 1
                self.log_ignore(error, "error substring matched")
                continue

            # Checking in file_specific_ignores
            if self.should_ignore_file_specific_error(file_path, error):
                self.count_of_ignored_errors += 1
                self.log_ignore(error, "file specific error")
                continue

            # Checking for "# pyright: off" mark
            if self.is_line_in_pyright_off_block(file_path, line_no):
                self.count_of_ignored_errors += 1
                self.log_ignore(error, "pyright disabled for this line")
                continue

            real_errors.append(error)

        return real_errors

    def get_all_files_to_check(self) -> set[str]:
        """Get all files to be analyzed by pyright, based on its config."""
        all_files: set[str] = set()

        if "include" in self.pyright_config_data:
            for dir_or_file in self.pyright_config_data["include"]:
                for file in self.get_all_py_files_recursively(dir_or_file):
                    all_files.add(file)
        else:
            # "include" is missing, we should analyze all files in current dir
            for file in self.get_all_py_files_recursively("."):
                all_files.add(file)

        if "exclude" in self.pyright_config_data:
            for dir_or_file in self.pyright_config_data["exclude"]:
                for file in self.get_all_py_files_recursively(dir_or_file):
                    if file in all_files:
                        all_files.remove(file)

        return all_files

    @staticmethod
    def get_all_py_files_recursively(dir_or_file: str) -> set[str]:
        """Return all python files in certain directory (or the file itself)."""
        if os.path.isfile(dir_or_file):
            return set(str(HERE / dir_or_file))

        all_files: set[str] = set()
        for root, _, files in os.walk(dir_or_file):
            for file in files:
                if file.endswith(".py"):
                    all_files.add(str(HERE / os.path.join(root, file)))

        return all_files

    def get_all_pyright_ignores(self) -> FileIgnores:
        """Get ignore information from all the files to be analyzed."""
        file_ignores: FileIgnores = {}
        for file in self.all_files_to_check:
            ignores = self.get_inline_type_ignores_from_file(file)
            if ignores:
                file_ignores[file] = ignores

        return file_ignores

    def get_pyright_off_ignores(self) -> FilePyrightOffIgnores:
        """Get ignore information based on `# pyright: on/off` marks."""
        pyright_off_ignores: FilePyrightOffIgnores = {}
        for file in self.all_files_to_check:
            ignores = self.find_pyright_off_from_file(file)
            if ignores:
                pyright_off_ignores[file] = ignores

        return pyright_off_ignores

    def get_unused_ignores(self) -> list[str]:
        """Evaluate if there are no ignores not matched by pyright errors."""
        unused_ignores: list[str] = []

        # type: ignore
        for file, file_ignores in self.all_pyright_ignores.items():
            for line_ignore in file_ignores:
                for ignore_statement in line_ignore.ignore_statements:
                    if not ignore_statement.already_used:
                        unused_ignores.append(
                            f"File {file}:{line_ignore.line_no + 1} has unused ignore. "
                            f"Substring: {ignore_statement.substring}"
                        )

        # Pyright: off
        for file, file_ignores in self.pyright_off_ignores.items():
            for off_ignore in file_ignores:
                if not off_ignore.already_used:
                    unused_ignores.append(
                        f"File {file} has unused # pyright: off ignore between lines "
                        f"{off_ignore.start_line + 1} and {off_ignore.end_line + 1}."
                    )

        # File-specific
        for file, file_ignores in self.file_specific_ignores.items():
            for ignore_object in file_ignores:
                if not ignore_object.already_used:
                    if ignore_object.substring:
                        unused_ignores.append(
                            f"File {file} has unused specific ignore substring. "
                            f"Substring: {ignore_object.substring}"
                        )
                    elif ignore_object.rule:
                        unused_ignores.append(
                            f"File {file} has unused specific ignore rule. "
                            f"Rule: {ignore_object.rule}"
                        )

        return unused_ignores

    def should_ignore_per_inline_substring(
        self, file: str, error_message: str, line_no: int
    ) -> bool:
        """Check if line should be ignored based on inline substring/regex."""
        if file not in self.all_pyright_ignores:
            return False

        for ignore_index, ignore in enumerate(self.all_pyright_ignores[file]):
            if line_no == ignore.line_no:
                for substring_index, ignore_statement in enumerate(
                    ignore.ignore_statements
                ):
                    # Supporting both text substrings and regex patterns
                    if ignore_statement.substring in error_message or re.search(
                        ignore_statement.substring, error_message
                    ):
                        # Marking this ignore to be used (so we can identify unused ignores)
                        self.all_pyright_ignores[file][ignore_index].ignore_statements[
                            substring_index
                        ].already_used = True
                        return True

        return False

    def should_ignore_file_specific_error(self, file: str, error: Error) -> bool:
        """Check if line should be ignored based on file-specific ignores."""
        if file not in self.file_specific_ignores:
            return False

        for ignore_object in self.file_specific_ignores[file]:
            if ignore_object.rule:
                if error["rule"] == ignore_object.rule:
                    ignore_object.already_used = True
                    return True
            elif ignore_object.substring:
                # Supporting both text substrings and regex patterns
                if ignore_object.substring in error["message"] or re.search(
                    ignore_object.substring, error["message"]
                ):
                    ignore_object.already_used = True
                    return True

        return False

    def is_line_in_pyright_off_block(self, file: str, line_no: int) -> bool:
        """Check if line should be ignored based on `# pyright: off` mark."""
        if file not in self.pyright_off_ignores:
            return False

        for off_ignore in self.pyright_off_ignores[file]:
            if off_ignore.start_line < line_no < off_ignore.end_line:
                off_ignore.already_used = True
                return True

        return False

    def find_pyright_off_from_file(self, file: str) -> PyrightOffIgnores:
        """Get sections in file to be ignored based on `# pyright: off`."""
        pyright_off_ignores: PyrightOffIgnores = []
        with open(file, "r") as f:
            pyright_off = False
            start_line = 0
            index = 0
            for index, line in enumerate(f):
                if self.OFF_PATTERN in line and not pyright_off:
                    start_line = index
                    pyright_off = True
                elif self.ON_PATTERN in line and pyright_off:
                    pyright_off_ignores.append(PyrightOffIgnore(start_line, index))
                    pyright_off = False

            if pyright_off:
                pyright_off_ignores.append(PyrightOffIgnore(start_line, index))

        return pyright_off_ignores

    def get_inline_type_ignores_from_file(self, file: str) -> LineIgnores:
        """Get all type ignore lines and statements from a certain file."""
        ignores: LineIgnores = []
        with open(file, "r") as f:
            for index, line in enumerate(f):
                if self.IGNORE_PATTERN in line:
                    ignore_statements = self.get_ignore_statements(line)
                    if not ignore_statements:
                        self.inconsistencies.append(
                            f"There is an empty `{self.IGNORE_PATTERN}` in {file}:{index+1}"
                        )
                    else:
                        ignores.append(LineIgnore(index, ignore_statements))

        return ignores

    def get_ignore_statements(self, line: str) -> list[IgnoreStatement]:
        """Extract error substrings to be ignored from a certain line."""
        # Extracting content of [error_substring(s)] after the ignore comment
        ignore_part = line.split(self.IGNORE_PATTERN, maxsplit=2)[1]
        ignore_content = re.search(r"\[(.*)\]", ignore_part)

        # We should not be using empty `# type: ignore` without content in []
        # Notifying the parent function that we should do something about it
        if not ignore_content:
            return []

        # There might be more than one substring
        statement_substrings = ignore_content.group(1).split(self.IGNORE_DELIMITER)

        # When finding aliases, replacing them with a real substring
        statement_substrings = [self.aliases.get(ss, ss) for ss in statement_substrings]

        return [IgnoreStatement(substr) for substr in statement_substrings]

    def log_ignore(self, error: Error, reason: str) -> None:
        """Print the action of ignoring certain error into the console."""
        if self.should_log:
            err = self.get_human_readable_error_string(error)
            print(f"\nError ignored. Reason: {reason}.\nErr: {err}")

    @staticmethod
    def get_human_readable_error_string(error: Error) -> str:
        """Transform error object to a string readable by human."""
        file = error["file"]
        message = error["message"]
        rule = error["rule"]
        line = error["range"]["start"]["line"]

        # Need to add +1 to the line, as it is zero-based index
        return f"{file}:{line + 1}: - error: {message} ({rule})\n"


if __name__ == "__main__":
    tool = PyrightTool(
        pyright_config_file=HERE / "pyrightconfig.json",
        file_specific_ignores={
            str(HERE / k): v for k, v in FILE_SPECIFIC_IGNORES.items()
        },
        aliases=ALIASES,
        error_file="errors_for_pyright_temp.json",
        should_generate_error_file=SHOULD_GENERATE_ERROR_FILE,
        should_delete_error_file=SHOULD_DELETE_ERROR_FILE,
        should_log=SHOULD_LOG,
    )
    tool.run()
