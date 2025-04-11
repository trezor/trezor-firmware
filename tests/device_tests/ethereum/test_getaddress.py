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

from trezorlib import ethereum
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowShowAddressQRCode

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


@parametrize_using_common_fixtures("ethereum/getaddress.json")
def test_getaddress(client: Client, parameters, result):
    address_n = parse_path(parameters["path"])
    assert (
        ethereum.get_address(client, address_n, show_display=True) == result["address"]
    )


@pytest.mark.models("core", reason="No input flow for T1")
@parametrize_using_common_fixtures("ethereum/getaddress.json")
def test_getaddress_chunkify_details(client: Client, parameters, result):
    with client:
        IF = InputFlowShowAddressQRCode(client)
        client.set_input_flow(IF.get())
        address_n = parse_path(parameters["path"])
        assert (
            ethereum.get_address(client, address_n, show_display=True, chunkify=True)
            == result["address"]
        )
