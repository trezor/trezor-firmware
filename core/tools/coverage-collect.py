#!/usr/bin/env python3
import json
import sys

import coverage

result_filename, *coverage_filenames = sys.argv[1:]

data = coverage.CoverageData(result_filename)

for filename in coverage_filenames:
    with open(filename) as f:
        file_map = json.load(f)
        lines = {}
        for file_path, values in file_map.items():
            # coverage doesn't support per-line counters
            lines[file_path] = [line for (line, _count) in values]
        data.add_lines(lines)

data.write()
