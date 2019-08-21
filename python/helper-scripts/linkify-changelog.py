#!/usr/bin/env python3

import os
import re

REPOS = {
    "": "python-trezor",
    "f": "trezor-firmware",
}

LINK_RE = re.compile(r"\[(f?)#(\d+)\]")
ISSUE_URL = "https://github.com/trezor/{repo}/issues/{issue}"

CHANGELOG = os.path.dirname(__file__) + "/../CHANGELOG.md"

changelog_entries = set()
links = set()
result_lines = []

with open(CHANGELOG, "r+") as changelog:
    for line in changelog:
        if LINK_RE.match(line):  # line *starts with* issue identifier
            break
        for repo, issue in LINK_RE.findall(line):
            changelog_entries.add((repo, int(issue)))
        result_lines.append(line)

    changelog.seek(0)
    changelog.truncate(0)
    for line in result_lines:
        changelog.write(line)
    for repo, issue in sorted(changelog_entries):
        url = ISSUE_URL.format(repo=REPOS[repo], issue=issue)
        changelog.write(f"[{repo}#{issue}]: {url}\n")
