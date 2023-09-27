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

from trezorlib.binance import get_address
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...input_flows import InputFlowShowAddressQRCode

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.binance,
    pytest.mark.skip_t1,  # T1 support is not planned
    pytest.mark.setup_client(
        mnemonic="offer caution gift cross surge pretty orange during eye soldier popular holiday mention east eight office fashion ill parrot vault rent devote earth cousin"
    ),
]

BINANCE_ADDRESS_TEST_VECTORS = [
    ("m/44h/714h/0h/0/0", "bnb1hgm0p7khfk85zpz5v0j8wnej3a90w709vhkdfu"),
    ("m/44h/714h/0h/0/1", "bnb1egswqkszzfc2uq78zjslc6u2uky4pw46x4rstd"),
]


@pytest.mark.parametrize("path, expected_address", BINANCE_ADDRESS_TEST_VECTORS)
def test_binance_get_address(client: Client, path: str, expected_address: str):
    # data from https://github.com/binance-chain/javascript-sdk/blob/master/__tests__/crypto.test.js#L50

    address = get_address(client, parse_path(path), show_display=True)
    assert address == expected_address


@pytest.mark.parametrize("path, expected_address", BINANCE_ADDRESS_TEST_VECTORS)
def test_binance_get_address_chunkify_details(
    client: Client, path: str, expected_address: str
):
    # data from https://github.com/binance-chain/javascript-sdk/blob/master/__tests__/crypto.test.js#L50

    with client:
        IF = InputFlowShowAddressQRCode(client)
        client.set_input_flow(IF.get())
        address = get_address(
            client, parse_path(path), show_display=True, chunkify=True
        )
        assert address == expected_address
