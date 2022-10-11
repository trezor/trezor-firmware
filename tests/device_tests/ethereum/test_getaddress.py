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
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import UH_, parse_path

from ...common import COMMON_FIXTURES_DIR, parametrize_using_common_fixtures

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


@parametrize_using_common_fixtures("ethereum/getaddress.json")
def test_getaddress(client: Client, parameters, result):
    address_n = parse_path(parameters["path"])
    encoded_network_slip44 = UH_(address_n[1])
    if "definitions" in parameters:
        encoded_network_slip44 = parameters["definitions"].get(
            "slip44", encoded_network_slip44
        )

    encoded_network = ethereum.network_definition_from_dir(
        path=COMMON_FIXTURES_DIR / "ethereum" / "definitions-latest",
        slip44=encoded_network_slip44,
    )
    assert (
        ethereum.get_address(client, address_n, encoded_network=encoded_network)
        == result["address"]
    )


def test_getaddress_missing_extern_definitions(client: Client):
    path = "m/44'/6060'/0'/0/0"  # GoChain
    address_n = parse_path(path)

    with pytest.raises(TrezorFailure, match=r"DataError:.*Forbidden key path"):
        ethereum.get_address(client, address_n, encoded_network=None)
