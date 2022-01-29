# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

from typing import TYPE_CHECKING

from . import messages
from .protobuf import dict_to_proto
from .tools import expect, session

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address
    from .protobuf import MessageType


@expect(messages.BinanceAddress, field="address", ret_type=str)
def get_address(
    client: "TrezorClient", address_n: "Address", show_display: bool = False
) -> "MessageType":
    return client.call(
        messages.BinanceGetAddress(address_n=address_n, show_display=show_display)
    )


@expect(messages.BinancePublicKey, field="public_key", ret_type=bytes)
def get_public_key(
    client: "TrezorClient", address_n: "Address", show_display: bool = False
) -> "MessageType":
    return client.call(
        messages.BinanceGetPublicKey(address_n=address_n, show_display=show_display)
    )


@session
def sign_tx(
    client: "TrezorClient", address_n: "Address", tx_json: dict
) -> messages.BinanceSignedTx:
    msg = tx_json["msgs"][0]
    envelope = dict_to_proto(messages.BinanceSignTx, tx_json)
    envelope.msg_count = 1
    envelope.address_n = address_n

    response = client.call(envelope)

    if not isinstance(response, messages.BinanceTxRequest):
        raise RuntimeError(
            "Invalid response, expected BinanceTxRequest, received "
            + type(response).__name__
        )

    if "refid" in msg:
        msg = dict_to_proto(messages.BinanceCancelMsg, msg)
    elif "inputs" in msg:
        msg = dict_to_proto(messages.BinanceTransferMsg, msg)
    elif "ordertype" in msg:
        msg = dict_to_proto(messages.BinanceOrderMsg, msg)
    else:
        raise ValueError("can not determine msg type")

    response = client.call(msg)

    if not isinstance(response, messages.BinanceSignedTx):
        raise RuntimeError(
            "Invalid response, expected BinanceSignedTx, received "
            + type(response).__name__
        )

    return response
