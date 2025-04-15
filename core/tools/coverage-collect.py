#!/usr/bin/env python3
import coverage
import json
import sys

result_filename, *coverage_filenames = sys.argv[1:]

data = coverage.CoverageData(result_filename)

for filename in coverage_filenames:
    with open(filename) as f:
        lines = json.load(f)
        data.add_lines(lines)

data.write()
