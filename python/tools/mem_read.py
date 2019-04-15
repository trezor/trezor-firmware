#!/usr/bin/env python3
from trezorlib.debuglink import DebugLink
from trezorlib.transport import enumerate_devices
import sys

# usage examples
# read entire bootloader: ./mem_read.py 8000000 8000
# read initial stack pointer: ./mem_read.py 8000000 4
# an entire bootloader can be later disassembled with:
# arm-none-eabi-objdump -D -b binary -m arm -M force-thumb memory.dat
# note that in order for this to work, your trezor device must
# be running a firmware that was built with debug link enabled


def find_debug():
    for device in enumerate_devices():
        try:
            debug_transport = device.find_debug()
            debug = DebugLink(debug_transport, auto_interact=False)
            debug.open()
            return debug
        except Exception:
            continue
    else:
        print("No suitable Trezor device found")
        sys.exit(1)


def main():
    debug = find_debug()

    arg1 = int(sys.argv[1], 16)
    arg2 = int(sys.argv[2], 16)
    step = 0x400 if arg2 >= 0x400 else arg2

    f = open("memory.dat", "wb")

    for addr in range(arg1, arg1 + arg2, step):
        mem = debug.memory_read(addr, step)
        f.write(mem)

    f.close()


if __name__ == "__main__":
    main()
