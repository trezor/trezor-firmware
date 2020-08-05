# generated from resources.py.mako
# do not edit manually!
# flake8: noqa
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
    if False:
        raise RuntimeError
% for resfile in resfiles:
    elif name == "${resfile.relative_to(SRCDIR)}":
        return ${repr(resfile.read_bytes())}
% endfor
    else:
        return bytes()
