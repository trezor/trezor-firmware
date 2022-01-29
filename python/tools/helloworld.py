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

from trezorlib import btc
from trezorlib.client import get_default_client
from trezorlib.tools import parse_path


def main() -> None:
    # Use first connected device
    client = get_default_client()

    # Print out Trezor's features and settings
    print(client.features)

    # Get the first address of first BIP44 account
    bip32_path = parse_path("44'/0'/0'/0/0")
    address = btc.get_address(client, "Bitcoin", bip32_path, True)
    print("Bitcoin address:", address)


if __name__ == "__main__":
    main()
