// generated from ${THIS_FILE.name}
// (by running `make templates` in `core`)
// do not edit manually!
// fmt: off
<%
from itertools import chain

SRCDIR = THIS_FILE.resolve().parent.parent.parent / "src"

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
    "monero",
    "nem",
    "ripple",
    "solana",
    "stellar",
    "tezos",
    "webauthn",
    "zcash",
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

imports_thp = [import_name for import_name in imports if ".thp" in import_name.lower()]
imports_common = [import_name for import_name in imports if (not any(a in import_name.lower() for a in ALTCOINS) and import_name not in imports_thp)]
imports_altcoin = [import_name for import_name in imports if import_name not in imports_common and import_name not in imports_thp]

def make_import_qstrs(import_names):
    imported = set()
    for name in import_names:
        for qstr in (name, name.rsplit('.', 1)[-1]):
            if qstr not in imported:
                yield qstr
                imported.add(qstr)
%>\

#error This header should not be part of the build, its purpose is only to add missed Qstrings

// explanation:
// uPy collects string literals and symbol names from all frozen modules, and
// converts them to qstrings for certain usages. In particular, it appears that
// qualified names of modules in sys.modules must be qstrings. However, the
// collection process is imperfect. If `apps.common.mnemonic` is always imported
// as `from ..common import mnemonic`, the string "apps.common.mnemonic" never
// appears in source code, is never collected, but then is generated and
// interned at runtime. A similar thing happens in reverse: if module
// `storage.cache` is always imported as this name, then "storage.cache" is
// collected but neither "storage" nor "cache" alone. Which is a problem,
// because "cache" is a symbol that is added to `storage`'s dict.
//
// We need to avoid run-time interning as much as possible, because it creates
// uncollectable garbage in the GC arena.

% for import_name in make_import_qstrs(imports_common):
Q(${import_name})
% endfor

#if USE_THP
% for import_name in make_import_qstrs(imports_thp):
Q(${import_name})
% endfor
#endif

#if !BITCOIN_ONLY
% for import_name in make_import_qstrs(imports_altcoin):
Q(${import_name})
% endfor
#endif

// generate full alphabet
<%
ALPHABET = "abcdefghijklmnopqrstuvwxyz"
%>\
% for letter in ALPHABET:
Q(${letter})
Q(${letter.upper()})
% endfor

// generate module presizing identifiers
% for i in range(30):
Q(___PRESIZE_MODULE_${i})
% endfor

Q())
Q(()
Q(<)
Q(;)
