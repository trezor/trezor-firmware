// generated from ${THIS_FILE.name}
// (by running `make templates` in `core`)
// do not edit manually!
#pragma GCC diagnostic ignored "-Wunused-value"
#pragma GCC diagnostic ignored "-Wunused-function"

static void _librust_qstrs(void) {
<%
import subprocess
import sys
from pathlib import Path
from typing import Union, Set

RUST_SRC = THIS_FILE.parent / "src"

ALTCOIN_PREFIXES = (
    "binance",
    "cardano",
    "eos",
    "ethereum",
    "fido",
    "monero",
    "nem",
    "ripple",
    "solana",
    "stellar",
    "tezos",
    "u2f",
)

def find_unique_patterns_in_dir(directory: Union[str, Path], pattern: str) -> Set[str]:
    command = f"grep -ro '{pattern}' {directory}"
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True, shell=True)
    output_lines = result.stdout.strip().split("\n")
    return set([line.split(":", 1)[1] for line in output_lines if line])

pattern = r"\bMP_QSTR_\w*"
qstrings = find_unique_patterns_in_dir(RUST_SRC, pattern)

qstrings_universal = set()
for prefix in ALTCOIN_PREFIXES:
    mp_prefix = f"MP_QSTR_{prefix}__"
    qstrings_universal |= {qstr for qstr in qstrings if qstr.startswith(mp_prefix)}

qstrings_btconly = qstrings - qstrings_universal

# sort result alphabetically
qstrings_btconly_sorted = sorted(qstrings_btconly)
qstrings_universal_sorted = sorted(qstrings_universal)
%>\
% for qstr in qstrings_btconly_sorted:
  ${qstr};
% endfor
#if !BITCOIN_ONLY
% for qstr in qstrings_universal_sorted:
  ${qstr};
% endfor
#endif
}
