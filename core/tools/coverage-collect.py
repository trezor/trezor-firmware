#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

import coverage

result_filename, *coverage_filenames = sys.argv[1:]

data = coverage.CoverageData(result_filename)


def to_preprocessed_path(py_path: Path) -> Path:
    # Remap <prefix>/src/<rel>.py → <prefix>/build/unix/src/<rel>.i so coverage
    # reports against the preprocessed source actually compiled into the frozen
    # build (dead feature-flag branches already rewritten to `if False:`).
    # Fall back to the original .py path when no .i exists (e.g. unfrozen
    # debug-only modules loaded directly from src/).
    path_parts = py_path.parts
    if py_path.suffix != ".py" or "src" not in path_parts:
        return py_path
    src_index = path_parts.index("src")
    prefix = path_parts[:src_index]
    rest = path_parts[src_index + 1 :]
    i_path = Path(*prefix) / "build/unix/src" / Path(*rest).with_suffix(".i")
    return i_path if os.path.exists(i_path) else py_path


for filename in coverage_filenames:
    with open(filename) as f:
        file_map = json.load(f)
        lines = {}
        for file_path, values in file_map.items():
            # coverage doesn't support per-line counters
            lines[str(to_preprocessed_path(Path(file_path)))] = [
                line for (line, _count) in values
            ]
        data.add_lines(lines)

data.write()
