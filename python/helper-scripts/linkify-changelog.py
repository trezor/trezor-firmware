#!/usr/bin/env python3

import os
import re

LINK_RE = re.compile(r"\[#(\d+)\]")
ISSUE_URL = "https://github.com/trezor/python-trezor/issues/"

CHANGELOG = os.path.dirname(__file__) + "/../CHANGELOG.md"

changelog_entries = set()
result_lines = []

with open(CHANGELOG, "r+") as changelog:
    for line in changelog:
        if ISSUE_URL in line:
            break
        for n in LINK_RE.findall(line):
            changelog_entries.add(int(n))
        result_lines.append(line)

    changelog.seek(0)
    changelog.truncate(0)
    for line in result_lines:
        changelog.write(line)
    for issue in sorted(changelog_entries):
        changelog.write(f"[#{issue}]: {ISSUE_URL}{issue}\n")
