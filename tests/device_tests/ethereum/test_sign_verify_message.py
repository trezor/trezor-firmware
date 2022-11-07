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

from ...common import parametrize_using_common_fixtures
from .ethereum_common import get_encoded_network_definition

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


@parametrize_using_common_fixtures("ethereum/signmessage.json")
def test_signmessage(client: Client, parameters, result):
    address_n = parse_path(parameters["path"])
    encoded_network_slip44 = UH_(address_n[1])
    if "definitions" in parameters:
        encoded_network_slip44 = parameters["definitions"].get(
            "slip44", encoded_network_slip44
        )

    encoded_network = get_encoded_network_definition(
        slip44=encoded_network_slip44,
    )

    res = ethereum.sign_message(client, address_n, parameters["msg"], encoded_network)
    assert res.address == result["address"]
    assert res.signature.hex() == result["sig"]


@parametrize_using_common_fixtures("ethereum/signmessage.failed.json")
def test_signmessage_failed(client: Client, parameters, result):
    address_n = parse_path(parameters["path"])
    encoded_network_slip44 = UH_(address_n[1])
    if "definitions" in parameters:
        encoded_network_slip44 = parameters["definitions"].get(
            "slip44", encoded_network_slip44
        )

    encoded_network = get_encoded_network_definition(
        slip44=encoded_network_slip44,
    )

    with pytest.raises(TrezorFailure, match=result["error"]):
        ethereum.sign_message(
            client, address_n, parameters["msg"], encoded_network=encoded_network
        )


@parametrize_using_common_fixtures("ethereum/verifymessage.json")
def test_verify(client: Client, parameters, result):
    res = ethereum.verify_message(
        client,
        parameters["address"],
        bytes.fromhex(parameters["sig"]),
        parameters["msg"],
    )
    assert res is True


def test_verify_invalid(client: Client):
    # First vector from the verifymessage JSON fixture
    msg = "This is an example of a signed message."
    address = "0xEa53AF85525B1779eE99ece1a5560C0b78537C3b"
    sig = bytes.fromhex(
        "9bacd833b51fde010bab53bafd9d832eadd3b175d2af2e629bb2944fcc987dce7ff68bb3571ed25a720c220f2f9538bc8d04f582bee002c9af086590a49805901c"
    )

    res = ethereum.verify_message(
        client,
        address,
        sig,
        msg,
    )
    assert res is True

    # Changing the signature, expecting failure
    res = ethereum.verify_message(
        client,
        address,
        sig[:-1] + b"\x00",
        msg,
    )
    assert res is False

    # Changing the message, expecting failure
    res = ethereum.verify_message(
        client,
        address,
        sig,
        msg + "abc",
    )
    assert res is False

    # Changing the address, expecting failure
    res = ethereum.verify_message(
        client,
        address[:-1] + "a",
        sig,
        msg,
    )
    assert res is False
