# generated from resources.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off
<%
from pathlib import Path
from itertools import chain

THIS = Path(local.filename).resolve()
SRCDIR = THIS.parent.parent.parent

PATTERNS = (
    "trezor/res/**/*.toif",
    "apps/*/res/**/*.toif",
)

resfiles = chain.from_iterable(sorted(SRCDIR.glob(p)) for p in PATTERNS)
%>\

def load_resource(name: str) -> bytes:
% for resfile in resfiles:
    if name == "${resfile.relative_to(SRCDIR)}":
        return ${repr(resfile.read_bytes())}
% endfor

    return bytes()
