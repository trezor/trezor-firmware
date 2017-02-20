#!/usr/bin/env python
from __future__ import print_function

from trezorlib.debuglink import DebugLink
from trezorlib.client import TrezorClient, TrezorDebugClient
from trezorlib.transport_hid import HidTransport
import binascii
import sys

# usage examples
# read entire bootloader: ./mem_read.py 8000000 8000
# read initial stack pointer: ./mem_read.py 8000000 4
# an entire bootloader can be later disassembled with:
# arm-none-eabi-objdump -D -b binary -m arm -M force-thumb memory.dat
# note that in order for this to work, your trezor device must
# be running a firmware that was built with debug link enabled

def main():
    # List all connected TREZORs on USB
    devices = HidTransport.enumerate()

    # Check whether we found any
    if len(devices) == 0:
        print('No TREZOR found')
        return

    # Use first connected device
    transport = HidTransport(devices[0])

    # Creates object for manipulating TREZOR
    debug_transport = HidTransport(devices[0], **{'debug_link': True})
    client = TrezorClient(transport)
    debug = DebugLink(debug_transport)

    arg1 = int(sys.argv[1], 16)
    arg2 = int(sys.argv[2], 16)
    step = 0x400 if arg2 >= 0x400 else arg2

    f = open('memory.dat', 'w')

    for addr in range(arg1, arg1 + arg2, step):
      mem = debug.memory_read(addr, step)
      f.write(mem)

    f.close()

    client.close()

if __name__ == '__main__':
    main()
