#!/usr/bin/env python3
from trezorlib.debuglink import DebugLink
from trezorlib.client import TrezorClient
from trezorlib.transport import enumerate_devices
import sys

sectoraddrs = [0x8000000, 0x8004000, 0x8008000, 0x800c000,
               0x8010000, 0x8020000, 0x8040000, 0x8060000,
               0x8080000, 0x80a0000, 0x80c0000, 0x80f0000]
sectorlens = [0x4000, 0x4000, 0x4000, 0x4000,
              0x8000, 0x10000, 0x10000, 0x10000,
              0x10000, 0x10000, 0x10000, 0x10000]


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

    sector = int(sys.argv[1])
    f = open(sys.argv[2], "rb")
    content = f.read(sectorlens[sector])
    if (len(content) != sectorlens[sector]):
        print("Not enough bytes in file")
        return

    debug.flash_erase(sector)
    step = 0x400
    for offset in range(0, sectorlens[sector], step):
        debug.memory_write(sectoraddrs[sector] + offset, content[offset:offset + step], flash=True)
    client.close()


if __name__ == '__main__':
    main()
