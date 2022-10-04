#!/usr/bin/env python3
"""
Showing sizes of individual micropython apps.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


from binsize import BinarySize, StatisticsPlugin, DataRow

HERE = Path(__file__).parent
CORE_DIR = HERE.parent.parent

if len(sys.argv) > 1:
    BIN_TO_ANALYZE = sys.argv[1]
else:
    BIN_TO_ANALYZE = CORE_DIR / "build/firmware/firmware.elf"  # type: ignore


def apps_categories(row: DataRow) -> str | None:
    pattern = r"^src/apps/(\w+)/"  # dir name after apps/
    match = re.search(pattern, row.module_name)
    if not match:
        return None
    else:
        return match.group(1)


if __name__ == "__main__":
    BS = (
        BinarySize()
        .load_file(BIN_TO_ANALYZE, sections=(".flash", ".flash2"))
        .use_map_file(
            CORE_DIR / "build/firmware/firmware.map", sections=(".flash", ".flash2")
        )
        .add_basic_info()
        .aggregate()
        .sort()
        .add_definitions()
    )
    StatisticsPlugin(BS, apps_categories).show()
