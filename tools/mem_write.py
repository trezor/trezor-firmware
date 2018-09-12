#!/usr/bin/env python3
from trezorlib.debuglink import DebugLink
from trezorlib.client import TrezorClient
from trezorlib.transport import enumerate_devices
import sys


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

    debug.memory_write(int(sys.argv[1], 16), bytes.fromhex(sys.argv[2]), flash=True)
    client.close()


if __name__ == '__main__':
    main()
