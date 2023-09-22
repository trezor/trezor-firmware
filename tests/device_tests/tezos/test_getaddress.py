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

from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tezos import get_address
from trezorlib.tools import parse_path

from ...input_flows import InputFlowShowAddressQRCode

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.tezos,
    pytest.mark.skip_t1,
]

TEST_VECTORS = [
    ("m/44h/1729h/0h", "tz1Kef7BSg6fo75jk37WkKRYSnJDs69KVqt9"),
    ("m/44h/1729h/1h", "tz1ekQapZCX4AXxTJhJZhroDKDYLHDHegvm1"),
]


@pytest.mark.parametrize("path, expected_address", TEST_VECTORS)
def test_tezos_get_address(client: Client, path: str, expected_address: str):
    address = get_address(client, parse_path(path), show_display=True)
    assert address == expected_address


@pytest.mark.parametrize("path, expected_address", TEST_VECTORS)
def test_tezos_get_address_chunkify_details(
    client: Client, path: str, expected_address: str
):
    with client:
        IF = InputFlowShowAddressQRCode(client)
        client.set_input_flow(IF.get())
        address = get_address(
            client, parse_path(path), show_display=True, chunkify=True
        )
        assert address == expected_address
