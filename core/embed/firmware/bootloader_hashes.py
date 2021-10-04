#!/usr/bin/env python3
import glob
try:
    from hashlib import blake2s
except ImportError:
    from pyblake2 import blake2s

ALIGNED_SIZE = 128 * 1024

files = glob.glob("bootloader*.bin")

for fn in sorted(files):
    data = open(fn, "rb").read()
    if len(data) > ALIGNED_SIZE:
        raise ValueError(fn, "too big")
    data_00 = data + b"\x00" * (ALIGNED_SIZE - len(data))
    data_ff = data + b"\xff" * (ALIGNED_SIZE - len(data))
    h_00 = blake2s(data=data_00).digest()
    h_ff = blake2s(data=data_ff).digest()
    h_00 = "".join(["\\x%02x" % i for i in h_00])
    h_ff = "".join(["\\x%02x" % i for i in h_ff])
    print("    // %s (padded with 0x00)\n    if (0 == memcmp(hash, \"%s\", 32)) return sectrue;" % (fn, h_00))
    print("    // %s (padded with 0xff)\n    if (0 == memcmp(hash, \"%s\", 32)) return sectrue;" % (fn, h_ff))
