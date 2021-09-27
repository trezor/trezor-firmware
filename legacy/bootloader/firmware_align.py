#!/usr/bin/env python3
import os
import sys

TOTALSIZE = 32768
MAXSIZE = TOTALSIZE - 32

fn = sys.argv[1]
fs = os.stat(fn).st_size
if fs > MAXSIZE:
    raise Exception(
        f"bootloader has to be smaller than {MAXSIZE} bytes (current size is {fs})"
    )
with open(fn, "ab") as f:
    f.write(b"\x00" * (TOTALSIZE - fs))
    f.close()
