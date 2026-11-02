"""Loads the app's message classes: the module `cargo app-tool gen-py` generates
from `protob/` for the device tests, regenerated whenever a .proto is newer."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

APP = Path(__file__).resolve().parents[2]
GENERATED = APP / "tests" / "generated" / "messages.py"


def load(name: str) -> ModuleType:
    """Imports the generated messages as module `name`."""
    newest = max(p.stat().st_mtime for p in (APP / "protob").glob("*.proto"))
    if not GENERATED.exists() or GENERATED.stat().st_mtime < newest:
        subprocess.run(
            ["cargo", "app-tool", "gen-py", "-p", APP.name],
            cwd=APP.parent,
            check=True,
            capture_output=True,
            text=True,
        )
    spec = importlib.util.spec_from_file_location(name, GENERATED)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
