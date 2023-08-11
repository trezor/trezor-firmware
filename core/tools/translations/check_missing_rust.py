from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).parent
CORE = HERE.parent.parent

RUST_DIR = CORE / "embed" / "rust" / "src" / "ui"
MAPPING_FILE = HERE / "mapping_rust.json"

IGNORE_FILES = ["cs.rs", "en.rs", "fr.rs", "general.rs", "fido_icons.rs"]
IGNORE_DIRS = ["bootloader"]


def extract_strings(file_path: Path) -> list[str]:
    with open(file_path, "r") as file:
        strings: list[str] = []
        line_starts_break = ["mod tests"]
        line_starts_pause = ["fn trace"]
        line_starts_continue = ["#[cfg", "//"]
        in_line_continue = [
            "Err(",
            "assert_if_debugging_ui",
            "panic!(",
            "value_error!(",
            "unwrap!(",
        ]
        is_paused = False
        for line in file:
            if is_paused:
                if line.startswith("}"):
                    is_paused = False
                continue
            if any([line.strip().startswith(start) for start in line_starts_break]):
                break
            if any([line.strip().startswith(start) for start in line_starts_pause]):
                is_paused = True
                continue
            if any([line.strip().startswith(start) for start in line_starts_continue]):
                continue
            if any([substr in line for substr in in_line_continue]):
                continue
            if "//" in line:
                line = line[: line.index("//")]
            new = re.findall(r'"(.*?)"', line)
            strings.extend(new)
        return strings


def ignore_string(string: str) -> bool:
    if string.endswith(".toif"):
        return True
    if string.startswith("model_"):
        return True
    if string.startswith("ui_"):
        return True
    if len(string) < 4:
        return True
    if "__" in string:
        return True
    return False


if __name__ == "__main__":
    all_rust_files = list(RUST_DIR.glob("**/*.rs"))
    all_strings: dict[str, list[str]] = {}
    for file_path in all_rust_files:
        if file_path.name in IGNORE_FILES:
            continue
        if any([ignore_dir in str(file_path) for ignore_dir in IGNORE_DIRS]):
            continue
        strings = extract_strings(file_path)
        strings = list(set(strings))
        strings = [s for s in strings if s]
        strings = [string for string in strings if not ignore_string(string)]
        if strings:
            all_strings[str(file_path)] = strings
    MAPPING_FILE.write_text(json.dumps(all_strings, indent=4))
