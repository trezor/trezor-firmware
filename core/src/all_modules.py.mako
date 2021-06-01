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

ALTCOINS = (
    "binance",
    "cardano",
    "eos",
    "ethereum",
    "lisk",
    "monero",
    "nem",
    "ripple",
    "stellar",
    "tezos",
    "webauthn",
)

pyfiles = chain.from_iterable(sorted(SRCDIR.glob(p)) for p in PATTERNS)

def make_import_name(pyfile):
    importfile = pyfile.relative_to(SRCDIR)
    if importfile.name == "__init__.py":
        import_name = str(importfile.parent)
    else:
        import_name = str(importfile.with_suffix(""))
    return import_name.replace("/", ".")

imports = [make_import_name(f) for f in pyfiles]

imports_common = [import_name for import_name in imports if not any(a in import_name.lower() for a in ALTCOINS)]
imports_altcoin = [import_name for import_name in imports if import_name not in imports_common]

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

from trezor import utils

% for import_name in imports_common:
${import_name}
import ${import_name}
% endfor

if utils.BITCOIN_ONLY:
% for import_name in imports_altcoin:
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
