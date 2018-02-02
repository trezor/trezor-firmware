#!/usr/bin/env python3
# example usage: ./rng_entropy_collector.py stm32_rng_1.dat 1048576
# note: for reading large amounts of entropy, compile a firmware
# that has DEBUG_RNG == 1 as that will disable the user button
# push confirmation

from __future__ import print_function
import io
import sys
from trezorlib.client import TrezorClient
from trezorlib.device import TrezorDevice


def get_client():
    devices = TrezorDevice.enumerate()    # list all connected TREZORs on USB
    if len(devices) == 0:                 # check whether we found any
        return None
    transport = devices[0]                # use first connected device
    return TrezorClient(transport)        # creates object for communicating with TREZOR


def main():
    client = get_client()
    if not client:
        print('No TREZOR connected')
        return

    arg1 = sys.argv[1]                     # output file
    arg2 = int(sys.argv[2], 10)            # total number of how many bytes of entropy to read
    step = 1024 if arg2 >= 1024 else arg2  # trezor will only return 1KB at a time

    with io.open(arg1, 'wb') as f:
        for i in range(0, arg2, step):
            entropy = client.get_entropy(step)
            f.write(entropy)

    client.close()


if __name__ == '__main__':
    main()
