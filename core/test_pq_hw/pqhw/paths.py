"""Where the suite keeps its persistent state: the source worktrees the
fixtures are built in, and the fixture set itself.

Outside the repository: the worktrees are full repo checkouts, and the repo's
own style targets walk the tree with `find` and reformat in place. Out here
nothing in the repo sees them, and branch switches leave nothing untracked.
Override with PQHW_HOME.
"""

from __future__ import annotations

import os
from pathlib import Path

HOME = Path(
    os.environ.get("PQHW_HOME") or Path.home() / ".local" / "share" / "trezor-pqhw"
)
WORK = HOME / "work"
FIXTURES = HOME / "fixtures"
