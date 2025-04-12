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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowEIP712Cancel, InputFlowEIP712ShowMore

pytestmark = [pytest.mark.altcoin, pytest.mark.ethereum]


@pytest.mark.models("core")
@parametrize_using_common_fixtures("ethereum/sign_typed_data.json")
def test_ethereum_sign_typed_data(client: Client, parameters, result):
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


@pytest.mark.models("legacy")
@parametrize_using_common_fixtures("ethereum/sign_typed_data.json")
def test_ethereum_sign_typed_data_blind(client: Client, parameters, result):
    with client:
        address_n = parse_path(parameters["path"])
        ret = ethereum.sign_typed_data_hash(
            client,
            address_n,
            ethereum.decode_hex(parameters["domain_separator_hash"]),
            # message hash is empty for domain-only hashes
            (
                ethereum.decode_hex(parameters["message_hash"])
                if parameters["message_hash"]
                else None
            ),
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


@pytest.mark.models("core")
def test_ethereum_sign_typed_data_show_more_button(client: Client):
    with client:
        client.watch_layout()
        IF = InputFlowEIP712ShowMore(client)
        client.set_input_flow(IF.get())
        ethereum.sign_typed_data(
            client,
            parse_path("m/44h/60h/0h/0/0"),
            DATA,
            metamask_v4_compat=True,
        )


@pytest.mark.models("core")
def test_ethereum_sign_typed_data_cancel(client: Client):
    with client, pytest.raises(exceptions.Cancelled):
        client.watch_layout()
        IF = InputFlowEIP712Cancel(client)
        client.set_input_flow(IF.get())
        ethereum.sign_typed_data(
            client,
            parse_path("m/44h/60h/0h/0/0"),
            DATA,
            metamask_v4_compat=True,
        )
