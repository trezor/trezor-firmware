"""Generates `messages.py` from the app's .proto files, the way tron's tests do."""

import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
PROTOB = APP / "protob"
OUT = Path(__file__).resolve().parent / "messages.py"


def ensure() -> None:
    protos = sorted(PROTOB.glob("*.proto"))
    template = PROTOB / "messages.py.mako"
    newest = max(p.stat().st_mtime for p in [*protos, template])
    if OUT.exists() and OUT.stat().st_mtime >= newest:
        return
    subprocess.run(
        [
            sys.executable,
            str(PROTOB / "pb2py"),
            "--template",
            str(template),
            "--outfile",
            str(OUT),
            *[str(p) for p in protos],
        ],
        cwd=APP,
        check=True,
        capture_output=True,
        text=True,
    )
