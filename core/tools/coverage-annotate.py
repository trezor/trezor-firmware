#!/usr/bin/env python3
import json
import sys
from collections import defaultdict

# Aggregate hits from all coverage JSON files
data = defaultdict(lambda: defaultdict(int))
for file_path in sys.argv[1:]:
    with open(file_path) as f:
        for src, values in json.load(f).items():
            per_file = data[src]
            for line, count in values:
                per_file[line] += count

# Print results using Markdown (for syntax highlighting)
for src, values in sorted(data.items()):
    count = sum(values.values())
    with open(src) as f:
        src_lines = [line.rstrip() for line in f]

    if not count or not src_lines:
        continue

    max_len = max(map(len, src_lines))
    print(f"### {src}")
    print("```python")
    for i, line in enumerate(src_lines):
        line = line.rstrip()
        count = values.get(i + 1)
        count = str(count) if count else ""
        pad = " " * (max_len - len(line))
        print(f"{line}{pad} # {count}")
    print("```")
