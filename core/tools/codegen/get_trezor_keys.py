#!/usr/bin/env python3

import binascii

from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport

devices = HidTransport.enumerate()
if len(devices) > 0:
    t = TrezorClient(devices[0])
else:
    raise Exception("No Trezor found")

for i in [0, 1, 2]:
    path = f"m/10018'/{i}'"
    pk = t.get_public_node(
        t.expand_path(path), ecdsa_curve_name="ed25519", show_display=True
    )
    print(path, "=>", binascii.hexlify(pk.node.public_key).decode())
