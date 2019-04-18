#!/usr/bin/env python3
import os
import sys

TOTALSIZE = 32768
MAXSIZE = TOTALSIZE - 32

fn = sys.argv[1]
fs = os.stat(fn).st_size
if fs > MAXSIZE:
    raise Exception(
        "bootloader has to be smaller than %d bytes (current size is %d)"
        % (MAXSIZE, fs)
    )
with open(fn, "ab") as f:
    f.write(b"\x00" * (TOTALSIZE - fs))
    f.close()
