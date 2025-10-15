#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

# example usage: ./rng_entropy_collector.py stm32_rng_1.dat 1048576
# note: for reading large amounts of entropy, compile a firmware
# that has DEBUG_RNG == 1 as that will disable the user button
# push confirmation

import io
import sys

from trezorlib import misc
from trezorlib.client import get_default_client, get_default_session


def main() -> None:
    try:
        client = get_default_client("rng_entropy_collector")
        session = get_default_session(client)
    except Exception as e:
        print(e)
        return

    arg1 = sys.argv[1]  # output file
    arg2 = int(sys.argv[2], 10)  # total number of how many bytes of entropy to read
    step = 1024 if arg2 >= 1024 else arg2  # trezor will only return 1KB at a time

    with session:
        with io.open(arg1, "wb") as f:
            for _ in range(0, arg2, step):
                entropy = misc.get_entropy(session, step)
                f.write(entropy)


if __name__ == "__main__":
    main()
