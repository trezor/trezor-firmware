#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import os
import random
import string

from trezorlib import device
from trezorlib.debuglink import TrezorClientDebugLink
from trezorlib.transport import enumerate_devices, get_transport


def get_device():
    path = os.environ.get("TREZOR_PATH")
    if path:
        return get_transport(path)
    else:
        devices = enumerate_devices()
        for d in devices:
            if hasattr(d, "find_debug"):
                return d
        raise RuntimeError("No debuggable device found")


wirelink = get_device()
client = TrezorClientDebugLink(wirelink)
client.open()
device.wipe(client)
device.reset(client, no_backup=True)

i = 0

while True:
    # set private field
    device.apply_settings(client, use_passphrase=True)
    assert client.features.passphrase_protection is True
    device.apply_settings(client, use_passphrase=False)
    assert client.features.passphrase_protection is False

    # set public field
    label = "".join(random.choices(string.ascii_uppercase + string.digits, k=17))
    device.apply_settings(client, label=label)
    assert client.features.label == label

    print("iteration %d" % i)
    i = i + 1
