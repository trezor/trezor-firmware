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

"""
Use Trezor as a hardware key for opening EncFS filesystem!

Usage:

encfs --standard --extpass=./encfs_aes_getpass.py ~/.crypt ~/crypt
"""

import hashlib
import json
import os
import sys
from typing import TYPE_CHECKING, Sequence

import trezorlib
import trezorlib.misc
from trezorlib.client import TrezorClient
from trezorlib.tools import Address
from trezorlib.transport import enumerate_devices
from trezorlib.ui import ClickUI

version_tuple = tuple(map(int, trezorlib.__version__.split(".")))
if not (0, 11) <= version_tuple < (0, 14):
    raise RuntimeError("trezorlib version mismatch (required: 0.13, 0.12, or 0.11)")


if TYPE_CHECKING:
    from trezorlib.transport import Transport


def wait_for_devices() -> Sequence["Transport"]:
    devices = enumerate_devices()
    while not len(devices):
        sys.stderr.write("Please connect Trezor to computer and press Enter...")
        input()
        devices = enumerate_devices()

    return devices


def choose_device(devices: Sequence["Transport"]) -> "Transport":
    if not len(devices):
        raise RuntimeError("No Trezor connected!")

    if len(devices) == 1:
        try:
            return devices[0]
        except IOError:
            raise RuntimeError("Device is currently in use")

    i = 0
    sys.stderr.write("----------------------------\n")
    sys.stderr.write("Available devices:\n")
    for d in devices:
        try:
            client = TrezorClient(d, ui=ClickUI())
        except IOError:
            sys.stderr.write("[-] <device is currently in use>\n")
            continue

        if client.features.label:
            sys.stderr.write(f"[{i}] {client.features.label}\n")
        else:
            sys.stderr.write(f"[{i}] <no label>\n")
        client.close()
        i += 1

    sys.stderr.write("----------------------------\n")
    sys.stderr.write("Please choose device to use:")

    try:
        device_id = int(input())
        return devices[device_id]
    except Exception:
        raise ValueError("Invalid choice, exiting...")


def main() -> None:

    if "encfs_root" not in os.environ:
        sys.stderr.write(
            "\nThis is not a standalone script and is not meant to be run independently.\n"
        )
        sys.stderr.write(
            "\nUsage: encfs --standard --extpass=./encfs_aes_getpass.py ~/.crypt ~/crypt\n"
        )
        sys.exit(1)

    devices = wait_for_devices()
    transport = choose_device(devices)
    client = TrezorClient(transport, ui=ClickUI())

    rootdir = os.environ["encfs_root"]  # Read "man encfs" for more
    passw_file = os.path.join(rootdir, "password.dat")

    if not os.path.exists(passw_file):
        # New encfs drive, let's generate password

        sys.stderr.write("Please provide label for new drive: ")
        label = input()

        sys.stderr.write("Computer asked Trezor for new strong password.\n")

        # 32 bytes, good for AES
        trezor_entropy = trezorlib.misc.get_entropy(client, 32)
        urandom_entropy = os.urandom(32)
        passw = hashlib.sha256(trezor_entropy + urandom_entropy).digest()

        if len(passw) != 32:
            raise ValueError("32 bytes password expected")

        bip32_path = Address([10, 0])
        passw_encrypted = trezorlib.misc.encrypt_keyvalue(
            client, bip32_path, label, passw, False, True
        )

        data = {
            "label": label,
            "bip32_path": bip32_path,
            "password_encrypted_hex": passw_encrypted.hex(),
        }

        json.dump(data, open(passw_file, "w"))

    # Let's load password
    data = json.load(open(passw_file, "r"))

    passw = trezorlib.misc.decrypt_keyvalue(
        client,
        data["bip32_path"],
        data["label"],
        bytes.fromhex(data["password_encrypted_hex"]),
        False,
        True,
    )

    print(passw)


if __name__ == "__main__":
    main()
