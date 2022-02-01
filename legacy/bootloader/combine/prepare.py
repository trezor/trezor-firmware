#!/usr/bin/env python3

bl = open("bl.bin", "rb").read()
fw = open("fw.bin", "rb").read()
combined = bl + 32768 * b"\xff" + fw

open("combined.bin", "wb").write(combined)

print(f"bootloader : {len(bl)} bytes")
print(f"firmware   : {len(fw)} bytes")
print(f"combined   : {len(combined)} bytes")
