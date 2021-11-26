#!/usr/bin/env python3
# example usage: ./rng_entropy_collector.py stm32_rng_1.dat 1048576
# note: for reading large amounts of entropy, compile a firmware
# that has DEBUG_RNG == 1 as that will disable the user button
# push confirmation

import io
import sys

from trezorlib import misc, ui
from trezorlib.client import TrezorClient
from trezorlib.transport import get_transport


def main() -> None:
    try:
        client = TrezorClient(get_transport(), ui=ui.ClickUI())
    except Exception as e:
        print(e)
        return

    arg1 = sys.argv[1]  # output file
    arg2 = int(sys.argv[2], 10)  # total number of how many bytes of entropy to read
    step = 1024 if arg2 >= 1024 else arg2  # trezor will only return 1KB at a time

    with io.open(arg1, "wb") as f:
        for _ in range(0, arg2, step):
            entropy = misc.get_entropy(client, step)
            f.write(entropy)

    client.close()


if __name__ == "__main__":
    main()
