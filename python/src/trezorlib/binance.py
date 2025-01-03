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
from .tools import session

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address


def get_address(
    client: "TrezorClient",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> str:
    return client.call(
        messages.BinanceGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.BinanceAddress,
    ).address


def get_public_key(
    client: "TrezorClient", address_n: "Address", show_display: bool = False
) -> bytes:
    return client.call(
        messages.BinanceGetPublicKey(address_n=address_n, show_display=show_display),
        expect=messages.BinancePublicKey,
    ).public_key


@session
def sign_tx(
    client: "TrezorClient", address_n: "Address", tx_json: dict, chunkify: bool = False
) -> messages.BinanceSignedTx:
    msg = tx_json["msgs"][0]
    tx_msg = tx_json.copy()
    tx_msg["msg_count"] = 1
    tx_msg["address_n"] = address_n
    tx_msg["chunkify"] = chunkify
    envelope = dict_to_proto(messages.BinanceSignTx, tx_msg)

    client.call(envelope, expect=messages.BinanceTxRequest)

    if "refid" in msg:
        msg = dict_to_proto(messages.BinanceCancelMsg, msg)
    elif "inputs" in msg:
        msg = dict_to_proto(messages.BinanceTransferMsg, msg)
    elif "ordertype" in msg:
        msg = dict_to_proto(messages.BinanceOrderMsg, msg)
    else:
        raise ValueError("can not determine msg type")

    return client.call(msg, expect=messages.BinanceSignedTx)
