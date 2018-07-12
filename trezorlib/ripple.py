# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import base64
import struct

from . import messages
from . import tools
from .client import field
from .client import expect


@field('address')
@expect(messages.RippleAddress)
def get_address(client, address_n, show_display=False):
    return client.call(
        messages.RippleGetAddress(
            address_n=address_n, show_display=show_display))


@expect(messages.RippleSignedTx)
def sign_tx(client, address_n, msg: messages.RippleSignTx):
    msg.address_n = address_n
    return client.call(msg)


def create_sign_tx_msg(transaction) -> messages.RippleSignTx:
    if not all(transaction.get(k) for k in ("Fee", "Sequence", "TransactionType", "Amount", "Destination")):
        raise ValueError("Some of the required fields missing (Fee, Sequence, TransactionType, Amount, Destination")
    if transaction["TransactionType"] != "Payment":
        raise ValueError("Only Payment transaction type is supported")

    return messages.RippleSignTx(
        fee=transaction.get("Fee"),
        sequence=transaction.get("Sequence"),
        flags=transaction.get("Flags"),
        last_ledger_sequence=transaction.get("LastLedgerSequence"),
        payment=_create_payment(transaction),
    )


def _create_payment(transaction) -> messages.RipplePayment:
    return messages.RipplePayment(
        amount=transaction.get("Amount"),
        destination=transaction.get("Destination")
    )
