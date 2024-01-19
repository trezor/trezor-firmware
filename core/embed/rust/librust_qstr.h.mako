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

def find_unique_patterns_in_dir(directory: Union[str, Path], pattern: str) -> Set[str]:
    command = f"grep -ro '{pattern}' {directory}"
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True, shell=True)
    output_lines = result.stdout.strip().split("\n")
    return set([line.split(":", 1)[1] for line in output_lines if line])

pattern = r"\bMP_QSTR_\w*"
qstrings = find_unique_patterns_in_dir(RUST_SRC, pattern)
# sort result alphabetically
qstrings_sorted = sorted(qstrings)
%>\
% for qstr in qstrings_sorted:
  ${qstr};
% endfor
}
