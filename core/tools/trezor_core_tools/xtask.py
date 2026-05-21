from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    embed_dir = Path(__file__).resolve().parents[2] / "embed"
    command = ["cargo", "xtask", *sys.argv[1:]]
    result = subprocess.run(command, cwd=embed_dir, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
