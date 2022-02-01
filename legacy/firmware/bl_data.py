#!/usr/bin/env python
from hashlib import sha256

fn = "bootloader.dat"

data = open(fn, "rb").read()
if len(data) > 32768:
    raise Exception("bootloader has to be smaller than 32768 bytes")

data += b"\x00" * (32768 - len(data))

bh = sha256(sha256(data).digest()).digest()

bl_hash = ", ".join("0x%02x" % x for x in bytearray(bh))
bl_data = ", ".join("0x%02x" % x for x in bytearray(data))

with open("bl_data.h", "wt") as f:
    f.write(f"static const uint8_t bl_hash[32] = {{{bl_hash}}};\n")
    f.write(f"static const uint8_t bl_data[32768] = {{{bl_data}}};\n")

# make sure the last item listed in known_bootloader function
# is our bootloader
with open("bl_check.c", "rt") as f:
    hashes = []
    for l in f.readlines():
        if not len(l) >= 78 or not l.startswith('             "\\x'):
            continue
        l = l[14:78]
        h = ""
        for i in range(0, len(l), 4):
            h += l[i + 2 : i + 4]
        hashes.append(h)
    check = hashes[-2] + hashes[-1]
    if check != bh.hex():
        raise Exception("bootloader hash not listed in bl_check.c")
