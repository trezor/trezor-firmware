#!/usr/bin/env python3
"""
Check the consistency of QSTRs in the Rust code.
"""
from __future__ import annotations

import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CORE_DIR = HERE.parent
RUST_DIR = CORE_DIR / "embed/rust"
RUST_SRC = RUST_DIR / "src"
QSTR_FILE = RUST_DIR / "librust_qstr.h"


def _get_qstrs_with_counts() -> dict[str, int]:
    with open(QSTR_FILE, "r") as f:
        lines = f.readlines()

    symbol_counts: dict[str, int] = defaultdict(int)
    for line in lines:
        line = line.strip()
        if line.startswith("MP_QSTR"):
            qstr_name = line.rstrip(";")
            symbol_counts[qstr_name] += 1

    return symbol_counts


def _get_all_qstrs() -> set[str]:
    return set(_get_qstrs_with_counts().keys())


def _is_qstr_used(qstr: str) -> bool:
    return subprocess.call(["grep", "-qrw", qstr, RUST_SRC]) == 0


def main() -> None:
    all_good = True

    # Find duplicate QSTRs
    for qstr, count in _get_qstrs_with_counts().items():
        if count > 1:
            print(f"Duplicate QSTR: {qstr} {count}")
            all_good = False

    # Find unused QSTRs
    for qstr in _get_all_qstrs():
        if not _is_qstr_used(qstr):
            print(f"Unused QSTR: {qstr}")
            all_good = False

    if all_good:
        print("QSTR OK")
        sys.exit(0)
    else:
        print("FAIL - see results above")
        sys.exit(1)


if __name__ == "__main__":
    main()
