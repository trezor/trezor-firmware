// generated from ${THIS_FILE.name}
// (by running `make templates` in `core`)
// do not edit manually!
#pragma GCC diagnostic ignored "-Wunused-value"
#pragma GCC diagnostic ignored "-Wunused-function"

static void _librust_qstrs(void) {
<%
import json
import subprocess
import sys
from pathlib import Path
from typing import Union, Set

RUST_SRC = THIS_FILE.parent / "src"

def find_qstrs_in_dir() -> set[str]:
    pattern = r"\bMP_QSTR_\w*"
    # Avoid processing generated files here, to avoid the following race condition:
    # * If translations are updated, `translated_string.rs` is updated via `translated_string.rs.mako`.
    # * This template may be processed concurrently, and use an older version of `translated_string.rs`.
    # (see https://github.com/trezor/trezor-firmware/issues/7338)
    args = ["grep", "-ro", "--exclude-dir=generated", pattern, RUST_SRC]
    output_lines = subprocess.check_output(args, text=True).strip().split("\n")
    return {line.split(":", 1)[1] for line in output_lines if line}

def find_qstrs_from_translations() -> set[str]:
    # Add qstrs for translation IDs (see `translated_string.rs.mako`)
    en_data = json.loads((ROOT / "core" / "translations" / "en.json").read_text())
    return {f"MP_QSTR_{name}" for name in en_data["translations"]}

qstrings = find_qstrs_in_dir() | find_qstrs_from_translations()

qstrings_universal = set()
for prefix in ALTCOIN_PREFIXES:
    mp_prefix = f"MP_QSTR_{prefix}__"
    qstrings_universal |= {qstr for qstr in qstrings if qstr.startswith(mp_prefix)}

qstrings_debug = set()
for prefix in DEBUG_PREFIXES:
    mp_prefix = f"MP_QSTR_{prefix}__"
    qstrings_debug |= {qstr for qstr in qstrings if qstr.startswith(mp_prefix)}

qstrings_btconly = qstrings - qstrings_universal - qstrings_debug

# sort result alphabetically
digits = range(10)
qstrings_btconly_sorted = sorted(qstrings_btconly)
qstrings_universal_sorted = sorted(qstrings_universal)
qstrings_debug_sorted = sorted(qstrings_debug)
%>\
% for digit in digits:
  MP_QSTR_${digit};
% endfor
% for qstr in qstrings_btconly_sorted:
  ${qstr};
% endfor
#if !BITCOIN_ONLY
% for qstr in qstrings_universal_sorted:
  ${qstr};
% endfor
#endif
#if !PYOPT
% for qstr in qstrings_debug_sorted:
  ${qstr};
% endfor
#endif
}
