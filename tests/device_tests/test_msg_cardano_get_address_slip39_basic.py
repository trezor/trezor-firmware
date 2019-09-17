# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import pytest

from trezorlib.cardano import get_address
from trezorlib.tools import parse_path

from ..common import MNEMONIC_SLIP39_BASIC_20_3of6


@pytest.mark.altcoin
@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.parametrize(
    "path,expected_address",
    [
        (
            "m/44'/1815'/0'/0/0",
            "Ae2tdPwUPEYxF9NAMNdd3v2LZoMeWp7gCZiDb6bZzFQeeVASzoP7HC4V9s6",
        ),
        (
            "m/44'/1815'/0'/0/1",
            "Ae2tdPwUPEZ1TjYcvfkWAbiHtGVxv4byEHHZoSyQXjPJ362DifCe1ykgqgy",
        ),
        (
            "m/44'/1815'/0'/0/2",
            "Ae2tdPwUPEZGXmSbda1kBNfyhRQGRcQxJFdk7mhWZXAGnapyejv2b2U3aRb",
        ),
    ],
)
@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6, passphrase=True)
def test_cardano_get_address(client, path, expected_address):
    # enter passphrase
    assert client.features.passphrase_protection is True
    client.set_passphrase("TREZOR")

    address = get_address(client, parse_path(path))
    assert address == expected_address
