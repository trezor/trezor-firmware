#!/usr/bin/env python3
"""Check that every GitHub Actions job declares a `timeout-minutes`.

Without it a job inherits GitHub's 6h default, so a hung test blocks the
runner for hours instead of failing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"

# Reusable-workflow calls cannot declare `timeout-minutes`.
REUSABLE_WORKFLOWS = ("./.github/workflows/crowdin-ui-check-reuse.yml",)


def main() -> int:
    failed = False

    for path in sorted(WORKFLOWS.glob("*.yml")):
        workflow = yaml.safe_load(path.read_text()) or {}
        for name, job in workflow.get("jobs", {}).items():
            timeout = str(job.get("timeout-minutes") or "").strip()
            if job.get("uses") in REUSABLE_WORKFLOWS or timeout:
                continue
            print(
                f"{path.relative_to(REPO)}: job '{name}' has no valid timeout-minutes"
            )
            failed = True

    if failed:
        print(
            "\nEvery job needs an explicit `timeout-minutes` -- GitHub's default is 6h."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
