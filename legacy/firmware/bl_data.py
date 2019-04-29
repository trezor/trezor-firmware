#!/usr/bin/env python
from hashlib import sha256

fn = "bootloader.dat"

data = open(fn, "rb").read()
if len(data) > 32768:
    raise Exception("bootloader has to be smaller than 32768 bytes")

data += b"\x00" * (32768 - len(data))

h = sha256(sha256(data).digest()).digest()

bl_hash = ", ".join("0x%02x" % x for x in bytearray(h))
bl_data = ", ".join("0x%02x" % x for x in bytearray(data))

with open("bl_data.h", "wt") as f:
    f.write("static const uint8_t bl_hash[32] = {%s};\n" % bl_hash)
    f.write("static const uint8_t bl_data[32768] = {%s};\n" % bl_data)
