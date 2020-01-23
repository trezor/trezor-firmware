#!/usr/bin/env python3

bl = open("bl.bin", "rb").read()
fw = open("fw.bin", "rb").read()
combined = bl + 32768 * b"\xff" + fw

open("combined.bin", "wb").write(combined)

print("bootloader : %d bytes" % len(bl))
print("firmware   : %d bytes" % len(fw))
print("combined   : %d bytes" % len(combined))
