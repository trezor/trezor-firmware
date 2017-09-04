#!/usr/bin/env python
from __future__ import print_function

from trezorlib.debuglink import DebugLink
from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport
import binascii
import sys


def main():
    # List all connected TREZORs on USB
    devices = HidTransport.enumerate()

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

    debug.memory_write(int(sys.argv[1], 16), binascii.unhexlify(sys.argv[2]), flash=True)
    client.close()


if __name__ == '__main__':
    main()
