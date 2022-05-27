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

Simplified program flow (as it happens in PyrightTool.run()):
- extract and validate pyright config data from pyrightconfig.json
- collect all the pyright errors by actually running the pyright itself
- extract type-ignore information for all the files pyright was analyzing
- loop through all the pyright errors and try to match them against all the type-ignore rules
- if there are some unmatched errors, report them and exit with nonzero value
- also report unused ignores and other inconsistencies
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict  # for python38 support, must be used in type aliases
from typing import List  # for python38 support, must be used in type aliases
from typing import TYPE_CHECKING, Any, Iterator
from typing_extensions import (  # for python37 support, is not present in typing there
    Final,
    TypedDict,
)

import click

if TYPE_CHECKING:
    LineIgnores = List["LineIgnore"]

    FileIgnores = Dict[str, LineIgnores]
    FileSpecificIgnores = Dict[str, List["FileSpecificIgnore"]]

    PyrightOffIgnores = List["PyrightOffIgnore"]
    FilePyrightOffIgnores = Dict[str, PyrightOffIgnores]


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


class Summary(TypedDict):
    filesAnalyzed: int
    errorCount: int
    warningCount: int
    informationCount: int
    timeInSec: float


class PyrightResults(TypedDict):
    version: str
    time: str
    generalDiagnostics: list[Error]
    summary: Summary


@dataclass
class IgnoreStatement:
    substring: str
    already_used: bool = False


@dataclass
class LineIgnore:
    line_no: int
    ignore_statements: list[IgnoreStatement]


@dataclass
class FileSpecificIgnore:
    rule: str = ""
    substring: str = ""
    already_used: bool = False

    def __post_init__(self) -> None:
        if self.rule and self.substring:
            raise ValueError("Only one of rule|substring should be set")


@dataclass
class PyrightOffIgnore:
    start_line: int
    end_line: int
    already_used: bool = False


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
    real_errors: list[Error]
    unused_ignores: list[str]
    inconsistencies: list[str] = []

    def __init__(
        self,
        workdir: Path,
        pyright_config_file: io.TextIOWrapper,
        *,
        file_specific_ignores: FileSpecificIgnores | None = None,
        aliases: dict[str, str] | None = None,
        input_file: io.TextIOWrapper | None = None,
        error_file: io.TextIOWrapper | None = None,
        verbose: bool = False,
    ) -> None:
        # validate arguments
        if not pyright_config_file.readable():
            raise RuntimeError("pyright config file is not readable")
        if input_file is not None and not input_file.readable():
            raise RuntimeError("input file is not readable")
        if error_file is not None and not error_file.writable():
            raise RuntimeError("error file is not writable")

        # save config
        self.workdir = workdir.resolve()
        self.pyright_config_data = self.load_config(pyright_config_file)
        self.file_specific_ignores = file_specific_ignores or {}
        self.aliases = aliases or {}
        self.input_file = input_file
        self.error_file = error_file
        self.verbose = verbose

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

    def load_config(self, config: io.TextIOWrapper) -> dict[str, Any]:
        """Load pyright config and validate any errors."""
        try:
            return json.load(config)
        except json.decoder.JSONDecodeError as err:
            raise RuntimeError(
                f"Pyright config does not contain valid JSON! Err: {err}"
            ) from err

    def get_pyright_output(self) -> str:
        """Run pyright and return its output."""
        # generate config with enableTypeIgnoreComments: false
        config_data = self.pyright_config_data.copy()
        config_data["enableTypeIgnoreComments"] = False
        with tempfile.NamedTemporaryFile("w", suffix=".json", dir=self.workdir) as tmp:
            json.dump(config_data, tmp)
            tmp.flush()

            cmd = (
                "pyright",
                "--outputjson",
                "--project",
                str(Path(tmp.name).resolve()),
            )

            # run pyright with generated config
            result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)

        # Checking if there was no non-type-checking error when running the above command
        # Exit code 0 = all fine, no type-checking issues in pyright
        # Exit code 1 = pyright has found some type-checking issues (expected)
        # All other exit codes mean something non-type-related got wrong (or pyright was not found)
        # https://github.com/microsoft/pyright/blob/main/docs/command-line.md#pyright-exit-codes
        if result.returncode not in (0, 1):
            raise RuntimeError(
                f"Running '{' '.join(cmd)}' produced a non-expected exit code (see output above)."
            )

        if not result.stdout:
            raise RuntimeError(
                f"Running '{' '.join(cmd)}' produced no data (see output above)."
            )

        return result.stdout

    def get_original_pyright_results(self) -> PyrightResults:
        """Extract pyright results data in a structured format.

        That means either running `pyright --outputjson`, or loading the provided JSON
        file created by an earlier run.
        """
        if self.input_file is not None:
            pyright_result_str = self.input_file.read()
        else:
            pyright_result_str = self.get_pyright_output()

        if self.error_file is not None:
            self.error_file.write(pyright_result_str)

        try:
            pyright_results: PyrightResults = json.loads(pyright_result_str)
        except json.decoder.JSONDecodeError as err:
            raise RuntimeError(
                f"Input error file does not contain valid JSON! Err: {err}"
            ) from None

        return pyright_results

    def get_all_real_errors(self) -> list[Error]:
        """Analyze all pyright errors and discard all that should be ignored.

        Ignores can be different:
        - as per "# type: ignore [<error_substring>]" comment
        - as per "file_specific_ignores"
        - as per "# pyright: off" mark
        """
        real_errors: list[Error] = []
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
        all_files: set[Path] = set()

        def _all_files(entry: str) -> Iterator[Path]:
            file_or_dir = Path(self.workdir / entry)
            if file_or_dir.is_file():
                yield file_or_dir
            else:
                yield from file_or_dir.glob("**/*.py")

        # include all relevant files.
        # use either the entries in `include`, or the current directory
        for entry in self.pyright_config_data.get("include", ("",)):
            all_files.update(_all_files(entry))

        # exclude specified files
        for entry in self.pyright_config_data.get("exclude", ()):
            all_files -= set(_all_files(entry))

        return {str(f) for f in all_files}

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
        if self.verbose:
            err = self.get_human_readable_error_string(error)
            print(f"\nError ignored. Reason: {reason}.\nErr: {err}")

    @staticmethod
    def get_human_readable_error_string(error: Error) -> str:
        """Transform error object to a string readable by human."""
        file = error["file"]
        message = error["message"]
        rule = error.get("rule", "No specific rule")
        line = error["range"]["start"]["line"]

        # Need to add +1 to the line, as it is zero-based index
        return f"{file}:{line + 1}: - error: {message} ({rule})\n"


@click.command()
@click.argument(
    "workdir", type=click.Path(exists=True, file_okay=False, dir_okay=True), default="."
)
@click.option(
    "--config",
    type=click.File("r"),
    help="Pyright configuration file. Defaults to pyrightconfig.json in the selected (or current) directory.",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    type=click.File("w"),
    help="Save pyright JSON output to file",
)
@click.option(
    "-i",
    "--input",
    "input_file",
    type=click.File("r"),
    help="Use input file instead of running pyright",
)
@click.option("-v", "--verbose", is_flag=True, help="Print verbose output")
def main(
    config: io.TextIOWrapper | None,
    input_file: io.TextIOWrapper | None,
    output_file: io.TextIOWrapper | None,
    verbose: bool,
    workdir: str | Path,
) -> None:
    workdir = Path(workdir)
    if config is None:
        config_path = workdir / "pyrightconfig.json"
        try:
            config = open(config_path)
        except Exception:
            raise click.ClickException(f"Failed to load {config_path}")

    try:
        tool = PyrightTool(
            workdir=workdir,
            pyright_config_file=config,
            file_specific_ignores=FILE_SPECIFIC_IGNORES,
            aliases=ALIASES,
            input_file=input_file,
            error_file=output_file,
            verbose=verbose,
        )
        tool.run()
    except Exception as e:
        raise click.ClickException(str(e)) from e


if __name__ == "__main__":
    main()
