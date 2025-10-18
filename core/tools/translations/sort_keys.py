#!/usr/bin/env python3
# pyright: reportMissingImports=false
import json
import sys
from enum import Enum, auto
from pathlib import Path

from helpers import ALL_LANGUAGES, TRANSLATIONS_DIR


class FileStatus(Enum):
    OK = auto()
    STYLE_ERROR = auto()
    FATAL_ERROR = auto()


def process_file(lang_file: Path, check_only: bool) -> FileStatus:
    """Returns FileStatus: OK, STYLE_ERROR, or FATAL_ERROR."""
    try:
        original_text = lang_file.read_text(encoding="utf-8")
        lang_data = json.loads(original_text)
    except json.JSONDecodeError as e:
        # always print the file name for easier debugging
        print(f"[INVALID] {lang_file}: {e}")
        return FileStatus.FATAL_ERROR

    formatted_text = (
        json.dumps(lang_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )

    if original_text == formatted_text:
        return FileStatus.OK

    if check_only:
        # in the check mode, report style error
        print(f"[UNFORMATTED] {lang_file}")
        return FileStatus.STYLE_ERROR
    else:
        # fix the style error otherwise
        print(f"[FORMATTING] {lang_file}")
        lang_file.write_text(formatted_text, encoding="utf-8")
        return FileStatus.OK


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "format"
    check_only = mode == "check"

    errors = []

    for lang in ALL_LANGUAGES:
        lang_file = TRANSLATIONS_DIR / f"{lang}.json"
        status = process_file(lang_file, check_only)
        if status is not FileStatus.OK:
            errors.append(lang_file)

    if errors:
        print("\n[FAIL] Some files are invalid or not properly formatted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
