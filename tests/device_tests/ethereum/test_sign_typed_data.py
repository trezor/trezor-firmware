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

from trezorlib import ethereum, exceptions
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

SHOW_MORE = (143, 167)

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum, pytest.mark.skip_t1]


@parametrize_using_common_fixtures("ethereum/sign_typed_data.json")
def test_ethereum_sign_typed_data(client, parameters, result):
    with client:
        address_n = parse_path(parameters["path"])
        ret = ethereum.sign_typed_data(
            client,
            address_n,
            parameters["data"],
            metamask_v4_compat=parameters["metamask_v4_compat"],
        )
        assert ret.address == result["address"]
        assert f"0x{ret.signature.hex()}" == result["sig"]


# Being the same as the first object in ethereum/sign_typed_data.json
DATA = {
    "types": {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "Person": [
            {"name": "name", "type": "string"},
            {"name": "wallet", "type": "address"},
        ],
        "Mail": [
            {"name": "from", "type": "Person"},
            {"name": "to", "type": "Person"},
            {"name": "contents", "type": "string"},
        ],
    },
    "primaryType": "Mail",
    "domain": {
        "name": "Ether Mail",
        "version": "1",
        "chainId": 1,
        "verifyingContract": "0x1e0Ae8205e9726E6F296ab8869160A6423E2337E",
    },
    "message": {
        "from": {"name": "Cow", "wallet": "0xc0004B62C5A39a728e4Af5bee0c6B4a4E54b15ad"},
        "to": {"name": "Bob", "wallet": "0x54B0Fa66A065748C40dCA2C7Fe125A2028CF9982"},
        "contents": "Hello, Bob!",
    },
}


def input_flow_show_more(client):
    """Clicks show_more button wherever possible"""
    yield  # confirm domain
    client.debug.wait_layout()
    client.debug.click(SHOW_MORE)

    # confirm domain properties
    for _ in range(4):
        yield
        client.debug.press_yes()

    yield  # confirm message
    client.debug.wait_layout()
    client.debug.click(SHOW_MORE)

    yield  # confirm message.from
    client.debug.wait_layout()
    client.debug.click(SHOW_MORE)

    # confirm message.from properties
    for _ in range(2):
        yield
        client.debug.press_yes()

    yield  # confirm message.to
    client.debug.wait_layout()
    client.debug.click(SHOW_MORE)

    # confirm message.to properties
    for _ in range(2):
        yield
        client.debug.press_yes()

    yield  # confirm message.contents
    client.debug.press_yes()

    yield  # confirm final hash
    client.debug.press_yes()


def input_flow_cancel(client):
    """Clicks cancelling button"""
    yield  # confirm domain
    client.debug.press_no()


def test_ethereum_sign_typed_data_show_more_button(client):
    with client:
        client.watch_layout()
        client.set_input_flow(input_flow_show_more(client))
        ethereum.sign_typed_data(
            client,
            parse_path("m/44'/60'/0'/0/0"),
            DATA,
            metamask_v4_compat=True,
        )


def test_ethereum_sign_typed_data_cancel(client):
    with client, pytest.raises(exceptions.Cancelled):
        client.watch_layout()
        client.set_input_flow(input_flow_cancel(client))
        ethereum.sign_typed_data(
            client,
            parse_path("m/44'/60'/0'/0/0"),
            DATA,
            metamask_v4_compat=True,
        )
