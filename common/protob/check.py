#!/usr/bin/env python3
import os
import re
import sys
from glob import glob

error = False

MYDIR = os.path.dirname(__file__)

EXPECTED_PREFIX_RE = re.compile(r"messages-(\w+)\.proto")

for fn in sorted(glob(os.path.join(MYDIR, "messages-*.proto"))):
    with open(fn, "rt") as f:
        prefix = EXPECTED_PREFIX_RE.search(fn).group(1).capitalize()
        if prefix in ["Bitcoin", "Bootloader", "Common", "Crypto", "Management"]:
            continue
        if prefix == "Nem":
            prefix = "NEM"
        elif prefix == "Webauthn":
            prefix = "WebAuthn"
        for line in f:
            line = line.strip().split(" ")
            if line[0] not in ["enum", "message"]:
                continue
            if not line[1].startswith(prefix) and not line[1].startswith(
                "Debug" + prefix
            ):
                print("ERROR:", fn, line[1])
                error = True

if error:
    sys.exit(1)
