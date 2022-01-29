#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import sys

from trezorlib.debuglink import DebugLink
from trezorlib.transport import enumerate_devices

# fmt: off
sectoraddrs = [0x8000000, 0x8004000, 0x8008000, 0x800c000,
               0x8010000, 0x8020000, 0x8040000, 0x8060000,
               0x8080000, 0x80a0000, 0x80c0000, 0x80f0000]
sectorlens = [0x4000, 0x4000, 0x4000, 0x4000,
              0x8000, 0x10000, 0x10000, 0x10000,
              0x10000, 0x10000, 0x10000, 0x10000]
# fmt: on


def find_debug() -> DebugLink:
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


def main() -> None:
    debug = find_debug()

    sector = int(sys.argv[1])
    f = open(sys.argv[2], "rb")
    content = f.read(sectorlens[sector])
    if len(content) != sectorlens[sector]:
        print("Not enough bytes in file")
        return

    debug.flash_erase(sector)
    step = 0x400
    for offset in range(0, sectorlens[sector], step):
        debug.memory_write(
            sectoraddrs[sector] + offset, content[offset : offset + step], flash=True
        )


if __name__ == "__main__":
    main()
