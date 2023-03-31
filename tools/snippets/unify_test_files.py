"""
Makes some unifications and improvements in the testing file.
For example:
- makes sure the paths have the same structure everywhere ("m/44h/1h/0h/1/0")
    - parse_path("44'/1'/0'/1/1")
        ->
    - parse_path("m/44h/1h/0h/1/1")
- formats big numbers with underscores for better readability (30_090_000)
    - amount=30090000,
        ->
    - amount=30_090_000,
- if it encouters a path or address, it tries to find its counterpart
  and put it as a comment to this line (it requires a translation file)
    - address_n=parse_path("44h/1h/0h/1/1"),
        ->
    - address_n=parse_path("44h/1h/0h/1/1"),  # mjXZwmEi1z1MzveZrKUAo4DBgbdq4sBYT6
    ...
    - address="mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY",
        ->
    - address="mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY",  # 44h/1h/4h/0/2
- adds type hints to untyped "client" argument in functions
  and imports the type if needed
    -  def test_15_of_15(client):
        ->
    -  def test_15_of_15(client: Client):
    ...
    - import pytest
        ->
    - from trezorlib.debuglink import TrezorClientDebugLink as Client
    - import pytest

The implementation here relies a lot on regexes, it could be better
to use some syntax tree parser like https://github.com/Instagram/LibCST.

Usage:
- specifying TRANSLATION_FILE (optional)
- specifying FILES_TO_MODIFY
- call the script with possible flags - see `python unify_test_files.py --help`
"""
import json
import os
import re
from pathlib import Path
from typing import List

import click

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

TRANSLATION_FILE = HERE / "address_cache_all_all_seed.json"  # might be missing

TAKE_ALL_FILES = True
if TAKE_ALL_FILES:
    # All the device-test files
    test_dir = ROOT / "tests/device_tests"
    FILES_TO_MODIFY = list(test_dir.rglob("test*.py"))
else:
    FILES_TO_MODIFY = [
        ROOT / "tests/device_tests/bitcoin/test_signtx.py",
        ROOT / "tests/device_tests/bitcoin/test_multisig.py",
        ROOT / "tests/device_tests/bitcoin/test_signtx_segwit.py",
    ]
print(f"Modifying {len(FILES_TO_MODIFY)} files")


class FileUnifier:
    # Optional "m/" prefix, at least two (\d+([h'])?/) groups and then take the rest [\dh'/]*
    PATH_REGEX = r"(m/)?(\d+([h'])?/){2,}[\dh'/]*"

    def __init__(
        self,
        translation_file: str,
        files_to_modify: List[str],
        quiet: bool = False,
        check_only: bool = False,
    ) -> None:
        self.files_to_modify = files_to_modify
        self.quiet = quiet
        self.check_only = check_only
        self.would_be_was = "would be" if self.check_only else "was"

        # File might not exist, in that case not doing translation
        # Example content: {"44h/1h/0h/0/1": "mopZWqZZyQc3F2Sy33cvDtJchSAMsnLi7b"}
        if os.path.isfile(translation_file):
            with open(translation_file, "r") as file:
                path_to_address = json.load(file)
            self.translations = {
                **path_to_address,
                **{a: p for p, a in path_to_address.items()},
            }
        else:
            self.translations = {}
        print(
            f"{len(self.translations)} translations available (path/address and address/path)\n{80*'*'}"
        )

        # For statistical purposes
        self.changes_made = 0
        self.files_changed = set()

        # For reporting purposes and to pass data around easily
        self.new_lines: List[str]
        self.file: str
        self.line: str
        self.line_no: int

    def unify_files(self) -> None:
        for file in self.files_to_modify:
            self.modify_file(file)
        print(
            f"{self.changes_made} changes {self.would_be_was} made in {len(self.files_changed)} "
            f"files out of {len(self.files_to_modify)} analyzed"
        )

    def modify_file(self, file: str) -> None:
        """Read the file, modify lines and save them back into it."""
        self.new_lines = []
        self.file = file
        self.line_no = 1
        with open(file, "r") as f:
            for line in f:
                self.line = line
                self.modify_line()
                self.new_lines.append(self.line)
                self.line_no += 1

        self.whole_file_modifications()

        if not self.check_only:
            with open(file, "w") as f:
                f.writelines(self.new_lines)

    def whole_file_modifications(self) -> None:
        """Working with the whole file at once, after the line-by-line modifications ended."""
        self.add_client_import_if_relevant()

    def add_client_import_if_relevant(self) -> None:
        """Add import statement for the client type, but only if it is used and not there already."""
        # Checking if the client typing is really used
        # If not, exitting
        client_typing = "client: Client"
        for line in self.new_lines:
            if client_typing in line:
                break
        else:
            return

        # Checking if the wanted import is already there
        # If so, not continuing
        # (And when it is there imported some other way, isort will take care of it)
        import_statement = (
            "from trezorlib.debuglink import TrezorClientDebugLink as Client"
        )
        for line in self.new_lines:
            if line.startswith(import_statement):
                return

        # Adding the import line before the first import
        # (isort will then make sure it is correctly sorted)
        # (It is better than doing it afterwards, as the import might be multiline)
        for index, line in enumerate(self.new_lines):
            if line.startswith(("import", "from")):
                new_line = f"{import_statement}\n{line}"
                self.line = line  # For reporting purposes
                self.report_change(
                    "client import added",
                    new_line,
                )
                self.new_lines[index] = new_line
                break

    def modify_line(self) -> None:
        """What should be done to this line."""
        # Not interested in whole comment lines - not changing them
        if self.line.lstrip().startswith("#"):
            return

        # All modifiers should modify self.line
        modifiers = [
            self.path_to_uniform_format,
            self.path_to_address_translation,
            self.address_to_path_translation,
            self.format_long_numbers,
            self.add_client_type_to_function,
        ]
        for modifier in modifiers:
            modifier()

    def path_to_uniform_format(self) -> None:
        """Unifies all paths to the same format."""
        if path_match := re.search(self.PATH_REGEX, self.line):
            # Only interested in parse_path() function arguments
            if "parse_path" not in self.line:
                return

            def sanitize_path(m: re.Match) -> str:
                # with added "m/" at the beginning and with "h" instead of "'"
                path = m[0]
                if not path.startswith("m/"):
                    path = f"m/{path}"
                return path.replace("'", "h")

            new_line = re.sub(self.PATH_REGEX, sanitize_path, self.line)
            if new_line != self.line:
                self.report_change(
                    f"path sanitized - {path_match.group()}",
                    new_line,
                )
                self.line = new_line

    def path_to_address_translation(self) -> None:
        """Translate path to address according to translations file."""
        if path_match := re.search(self.PATH_REGEX, self.line):
            if address := self.translations.get(path_match.group()):
                # Address might be there from previous run
                if address not in self.line:
                    new_line = f"{self.line.rstrip()}  # {address}\n"
                    self.report_change(
                        f"path translated - {path_match.group()}",
                        new_line,
                    )
                    self.line = new_line

    def address_to_path_translation(self) -> None:
        """Translate address to path according to translations file."""
        address_regex = r"\b\w{33,35}\b"
        if address_match := re.search(address_regex, self.line):
            if path := self.translations.get(address_match.group()):
                # Path might be there from previous run
                if path not in self.line:
                    new_line = f"{self.line.rstrip()}  # {path}\n"
                    self.report_change(
                        f"address translated - {address_match.group()}",
                        new_line,
                    )
                    self.line = new_line

    def format_long_numbers(self) -> None:
        """Uses underscore delimiters in long integers."""
        long_number_regex = r"\d{4,}"
        if number_match := re.search(long_number_regex, self.line):
            # Do it for all the number-keyword-arguments
            if re.search(r"\w=[\d \+\*-/]+,", self.line):

                def num_to_underscore(m: re.Match) -> str:
                    # https://stackoverflow.com/questions/9475241/split-string-every-nth-character
                    # https://stackoverflow.com/questions/931092/reverse-a-string-in-python
                    parts_reversed = re.findall(".{1,3}", m[0][::-1])
                    return "_".join(parts_reversed)[::-1]

                new_line = re.sub(long_number_regex, num_to_underscore, self.line)
                if new_line != self.line:
                    self.report_change(
                        f"long number formatted - {number_match.group()}",
                        new_line,
                    )
                    self.line = new_line

    def add_client_type_to_function(self) -> None:
        """Includes the data type."""
        client_in_definition = r"(?:\bdef\b.*)\bclient\b"
        if client_match := re.search(client_in_definition, self.line):
            # Might be already typed
            if "client: Client" in self.line:
                return

            def add_type(m: re.Match) -> str:
                return f"{m[0]}: Client"

            new_line = re.sub(client_in_definition, add_type, self.line)
            if new_line != self.line:
                self.report_change(
                    f"client type added - {client_match.group()}",
                    new_line,
                )
                self.line = new_line

    def report_change(self, info: str, new_line: str) -> None:
        self.changes_made += 1
        self.files_changed.add(self.file)

        if self.quiet:
            return

        print(f"{self.file}:{self.line_no} {self.would_be_was} changed")
        print(info)
        print(self.line.strip())
        print(f"               {self.would_be_was} changed to")
        print(new_line.strip())
        print(80 * "*")


@click.command()
@click.option("-q", "--quiet", is_flag=True, help="Do not report")
@click.option("-c", "--check_only", is_flag=True, help="Do not rewrite")
def run_unifier(quiet: bool, check_only: bool) -> None:
    file_unifier = FileUnifier(
        translation_file=str(TRANSLATION_FILE),
        files_to_modify=[str(f) for f in FILES_TO_MODIFY],
        quiet=quiet,
        check_only=check_only,
    )
    file_unifier.unify_files()
    if not check_only:
        print("You may need/want to call `black` and `isort` on the changed files.")


if __name__ == "__main__":
    run_unifier()
