#!/usr/bin/env python3
from trezorlib.debuglink import DebugLink
from trezorlib.transport import enumerate_devices
import sys


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
    debug.memory_write(int(sys.argv[1], 16), bytes.fromhex(sys.argv[2]), flash=True)


if __name__ == "__main__":
    main()
