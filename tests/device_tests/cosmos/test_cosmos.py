# This file is part of the Trezor project.
#
# Copyright (C) 2012-2026 SatoshiLabs and contributors
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

from trezorlib import cosmos
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import (
    InputFlowConfirmAllWarnings,
    InputFlowShowAddressQRCode,
    InputFlowShowXpubQRCode,
)

pytestmark = [pytest.mark.altcoin, pytest.mark.models("core")]

PUBLIC_KEY_VECTORS = [
    (
        "m/44h/118h/0h/0/0",
        "/cosmos.crypto.secp256k1.PubKey",
        "02e1b06f14aac6d3f81ec57252aad688065f6fb52bfa029870043e46ef26201c50",
    ),
    (
        "m/44h/118h/1h/0/0",
        "/cosmos.crypto.secp256k1.PubKey",
        "0280b676e9379efabe0302e8eebf28ddbcd1339123b7ae046a396d96dd920f0a3d",
    ),
]


@parametrize_using_common_fixtures("cosmos/get_address.json")
def test_get_address(client: Client, parameters, result):
    address = cosmos.get_address(
        client,
        parse_path(parameters["path"]),
        parameters["prefix"],
        show_display=True,
    )
    assert address.address == result["address"]


@parametrize_using_common_fixtures("cosmos/get_address.json")
def test_get_address_chunkify_details(client: Client, parameters, result):
    with client:
        flow = InputFlowShowAddressQRCode(client)
        client.set_input_flow(flow.get())
        address = cosmos.get_address(
            client,
            parse_path(parameters["path"]),
            parameters["prefix"],
            show_display=True,
        )

    assert address.address == result["address"]


@pytest.mark.parametrize(
    "path, expected_type, expected_value",
    PUBLIC_KEY_VECTORS,
)
def test_get_public_key(
    client: Client, path: str, expected_type: str, expected_value: str
):
    with client:
        flow = InputFlowShowXpubQRCode(client)
        client.set_input_flow(flow.get())
        public_key = cosmos.get_public_key(
            client,
            parse_path(path),
            show_display=True,
        )

    assert public_key.type == expected_type
    assert public_key.value.hex() == expected_value


@parametrize_using_common_fixtures("cosmos/sign_tx.json")
def test_sign_tx(client: Client, parameters, result):
    with client:
        flow = InputFlowConfirmAllWarnings(client)
        client.set_input_flow(flow.get())
        response = cosmos.sign_tx(
            client,
            parse_path(parameters["path"]),
            bytes.fromhex(parameters["sign_doc"]),
        )

    assert response.signature.hex() == result["signature"]
