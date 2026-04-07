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

from io import BytesIO

import pytest

from trezorlib import cosmos, messages, protobuf
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import (
    InputFlowConfirmAllWarnings,
    InputFlowShowAddressQRCode,
    InputFlowShowXpubQRCode,
)

pytestmark = [pytest.mark.altcoin, pytest.mark.cosmos, pytest.mark.models("core")]

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


def dump_message(msg: protobuf.MessageType) -> bytes:
    writer = BytesIO()
    protobuf.dump_message(writer, msg)
    return writer.getvalue()


@parametrize_using_common_fixtures("cosmos/get_address.json")
def test_get_address(session: Session, parameters, result):
    address = cosmos.get_address(
        session,
        parse_path(parameters["path"]),
        parameters["prefix"],
        show_display=True,
    )
    assert address.address == result["address"]


@parametrize_using_common_fixtures("cosmos/get_address.json")
def test_get_address_chunkify_details(session: Session, parameters, result):
    with session.test_ctx as client:
        flow = InputFlowShowAddressQRCode(session)
        client.set_input_flow(flow.get())
        address = cosmos.get_address(
            session,
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
    session: Session, path: str, expected_type: str, expected_value: str
):
    with session.test_ctx as client:
        flow = InputFlowShowXpubQRCode(session)
        client.set_input_flow(flow.get())
        public_key = cosmos.get_public_key(
            session,
            parse_path(path),
            show_display=True,
        )

    assert public_key.key_type == expected_type
    assert public_key.value.hex() == expected_value


@parametrize_using_common_fixtures("cosmos/sign_tx.json")
def test_sign_tx(session: Session, parameters, result):
    with session.test_ctx as client:
        flow = InputFlowConfirmAllWarnings(session)
        client.set_input_flow(flow.get())
        response = cosmos.sign_tx(
            session,
            parse_path(parameters["path"]),
            bytes.fromhex(parameters["sign_doc"]),
        )

    assert response.signature.hex() == result["signature"]


def test_get_address_rejects_unsupported_prefix(session: Session) -> None:
    with pytest.raises(TrezorFailure, match="Unsupported address prefix"):
        cosmos.get_address(
            session,
            parse_path("m/44h/118h/0h/0/0"),
            "juno",
            show_display=False,
        )


def test_sign_tx_rejects_empty_message_list(session: Session) -> None:
    body_bytes = dump_message(messages.CosmosTxBody(messages=[]))
    signer_pubkey = dump_message(
        messages.CosmosSecp256k1Pubkey(
            key=bytes.fromhex(
                "02e1b06f14aac6d3f81ec57252aad688065f6fb52bfa029870043e46ef26201c50"
            )
        )
    )
    auth_info_bytes = dump_message(
        messages.CosmosAuthInfo(
            signer_infos=[
                messages.CosmosSignerInfo(
                    public_key=messages.CosmosAny(
                        type_url="/cosmos.crypto.secp256k1.PubKey",
                        value=signer_pubkey,
                    ),
                    mode_info=messages.CosmosModeInfo(
                        single=messages.CosmosModeInfoSingle(
                            mode=messages.CosmosSignMode.SIGN_MODE_DIRECT
                        )
                    ),
                    sequence=0,
                )
            ],
            fee=messages.CosmosFee(
                gas_limit=81000,
                amount=[messages.CosmosCoin(denom="uatom", amount="1234")],
            ),
        )
    )
    sign_doc = dump_message(
        messages.CosmosSignDoc(
            body_bytes=body_bytes,
            auth_info_bytes=auth_info_bytes,
            chain_id="cosmoshub-4",
            account_number=7,
        )
    )

    with session.test_ctx as client:
        flow = InputFlowConfirmAllWarnings(session)
        client.set_input_flow(flow.get())
        with pytest.raises(
            TrezorFailure, match="Transaction body must contain at least one message"
        ):
            cosmos.sign_tx(
                session,
                parse_path("m/44h/118h/0h/0/0"),
                sign_doc,
            )
