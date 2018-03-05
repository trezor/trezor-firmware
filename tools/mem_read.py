#!/usr/bin/env python3
from trezorlib.debuglink import DebugLink
from trezorlib.client import TrezorClient
from trezorlib.transport import enumerate_devices
import sys

# usage examples
# read entire bootloader: ./mem_read.py 8000000 8000
# read initial stack pointer: ./mem_read.py 8000000 4
# an entire bootloader can be later disassembled with:
# arm-none-eabi-objdump -D -b binary -m arm -M force-thumb memory.dat
# note that in order for this to work, your trezor device must
# be running a firmware that was built with debug link enabled


def main():
    # List all debuggable TREZORs
    devices = [device for device in enumerate_devices() if hasattr(device, 'find_debug')]

    # Check whether we found any
    if len(devices) == 0:
        print('No TREZOR found')
        return

    # Use first connected device
    transport = devices[0]
    debug_transport = devices[0].find_debug()

    # Creates object for manipulating TREZOR
    client = TrezorClient(transport)
    debug = DebugLink(debug_transport)

    arg1 = int(sys.argv[1], 16)
    arg2 = int(sys.argv[2], 16)
    step = 0x400 if arg2 >= 0x400 else arg2

    f = open('memory.dat', 'wb')

    for addr in range(arg1, arg1 + arg2, step):
        mem = debug.memory_read(addr, step)
        f.write(mem)

    f.close()

    client.close()


if __name__ == '__main__':
    main()
