#!/usr/bin/env python3
from glob import glob
import os
import sys

error = False

MYDIR = os.path.dirname(__file__)

for fn in sorted(glob(os.path.join(MYDIR, "messages-*.proto"))):
    with open(fn, "rt") as f:
        prefix = fn.split(".")[0][9:].capitalize()
        if prefix in ["Bitcoin", "Bootloader", "Common", "Crypto", "Management"]:
            continue
        if prefix == "Nem":
            prefix = "NEM"
        for line in f:
            line = line.strip().split(" ")
            if line[0] not in ["enum", "message"]:
                continue
            if not line[1].startswith(prefix) and not line[1].startswith("Debug" + prefix):
                print("ERROR:", fn, line[1])
                error = True

if error:
    sys.exit(1)
