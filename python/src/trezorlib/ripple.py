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
from .tools import dict_from_camelcase

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address

REQUIRED_FIELDS = ("Fee", "Sequence", "TransactionType", "Payment")
REQUIRED_PAYMENT_FIELDS = ("Amount", "Destination")


def get_address(
    client: "TrezorClient",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> str:
    return client.call(
        messages.RippleGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.RippleAddress,
    ).address


def sign_tx(
    client: "TrezorClient",
    address_n: "Address",
    msg: messages.RippleSignTx,
    chunkify: bool = False,
) -> messages.RippleSignedTx:
    msg.address_n = address_n
    msg.chunkify = chunkify
    return client.call(msg, expect=messages.RippleSignedTx)


def create_sign_tx_msg(transaction: dict) -> messages.RippleSignTx:
    if not all(transaction.get(k) for k in REQUIRED_FIELDS):
        raise ValueError("Some of the required fields missing")
    if not all(transaction["Payment"].get(k) for k in REQUIRED_PAYMENT_FIELDS):
        raise ValueError("Some of the required payment fields missing")
    if transaction["TransactionType"] != "Payment":
        raise ValueError("Only Payment transaction type is supported")

    converted = dict_from_camelcase(transaction)
    return dict_to_proto(messages.RippleSignTx, converted)
