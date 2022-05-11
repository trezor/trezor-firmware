#!/usr/bin/env python3

import sys
from hashlib import blake2s

FILE_T1 = "legacy/firmware/trezor.bin"
FILE_T2 = "core/build/firmware/firmware.bin"

T1_HEADER_MAGIC_OLD = b"TRZR"
T1_HEADER_OLD_SIZE = 256
T2_HEADER_MAGIC_VENDOR = b"TRZV"

SIZE_T1 = (7 * 128 + 64) * 1024
SIZE_T2 = 13 * 128 * 1024

if len(sys.argv) > 2:
    filenames = sys.argv[2:]
elif len(sys.argv) == 2:
    filenames = (FILE_T1, FILE_T2)
else:
    print(f"Usage: {sys.argv[0]} HEX_CHALLENGE [FILE]...")
    print(f"       HEX_CHALLENGE: a 0-32 byte challenge in hexadecimal")
    exit(1)


for filename in filenames:
    try:
        data = open(filename, "rb").read()
    except FileNotFoundError:
        print(f"{filename} not found")
        continue

    offset = 0
    if data[:4] == T2_HEADER_MAGIC_VENDOR:
        size = SIZE_T2
    else:
        size = SIZE_T1
        if data[:4] == T1_HEADER_MAGIC_OLD:
            offset = T1_HEADER_OLD_SIZE

    if len(data) - offset > size:
        raise ValueError(filename, "too big")
    data = data[offset:] + b"\xff" * (size - len(data) + offset)

    challenge = bytes.fromhex(sys.argv[1])
    firmware_hash = blake2s(data, key=challenge).hexdigest()
    print(f"{filename}: {firmware_hash}")
