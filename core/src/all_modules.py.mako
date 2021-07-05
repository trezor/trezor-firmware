# generated from all_modules.py.mako
# do not edit manually!
# flake8: noqa
# fmt: off
# isort:skip_file
<%
from pathlib import Path
from itertools import chain

THIS = Path(local.filename).resolve()
SRCDIR = THIS.parent

PATTERNS = (
    "*.py",
    "storage/**/*.py",
    "trezor/**/*.py",
    "apps/**/*.py",
)

pyfiles = chain.from_iterable(sorted(SRCDIR.glob(p)) for p in PATTERNS)
%>\
from trezor.utils import halt

# this module should not be part of the build, its purpose is only to add missed Qstrings
halt("Tried to import excluded module.")

# explanation:
# uPy collects string literals and symbol names from all frozen modules, and converts
# them to qstrings for certain usages. In particular, it appears that qualified names
# of modules in sys.modules must be qstrings. However, the collection process is
# imperfect. If `apps.common.mnemonic` is always imported as `from ..common import mnemonic`,
# the string "apps.common.mnemonic" never appears in source code, is never collected,
# but then is generated and interned at runtime.
# A similar thing happens in reverse: if module `storage.cache` is always imported as
# this name, then "storage.cache" is collected but neither "storage" nor "cache" alone.
# Which is a problem, because "cache" is a symbol that is added to `storage`'s dict.
#
# We need to avoid run-time interning as much as possible, because it creates
# uncollectable garbage in the GC arena.
#
# Below, every module is listed both as import (which collects the qualified name)
# and as a symbol (which collects each individual component).
# In addition, we list the alphabet, because apparently one-character strings are always
# interned, and some operation somewhere (rendering?) is reading strings character by
# character.

% for pyfile in pyfiles:
<%
pyfile = pyfile.relative_to(SRCDIR)
if pyfile.name == "__init__.py":
    import_name = str(pyfile.parent)
else:
    import_name = str(pyfile.with_suffix(""))
import_name = import_name.replace("/", ".")
%>\
${import_name}
import ${import_name}
% endfor

# generate full alphabet
<%
ALPHABET = "abcdefghijklmnopqrstuvwxyz"
%>\
% for letter in ALPHABET:
${letter}
${letter.upper()}
% endfor
