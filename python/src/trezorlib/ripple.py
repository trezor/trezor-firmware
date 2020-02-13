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

from . import messages
from .protobuf import dict_to_proto
from .tools import dict_from_camelcase, expect

REQUIRED_FIELDS = {
    "Common": ["Fee", "Sequence", "TransactionType"],
    "Payment": [["Amount", "IssuedAmount"], "Destination"],
    "SetRegularKey": [],
    "EscrowCreate": ["Amount", "Destination"],
    "EscrowCancel": ["Owner", "OfferSequence"],
    "EscrowFinish": ["Owner", "OfferSequence"],
    "AccountSet": [],
    "PaymentChannelCreate": ["Amount", "Destination", "SettleDelay", "PublicKey"],
    "PaymentChannelFund": ["Channel", "Amount"],
    "PaymentChannelClaim": ["Channel"],
    "TrustSet": ["LimitAmount"],
    "OfferCreate": [["TakerGets", "IssuedTakerGets"], ["TakerPays", "IssuedTakerPays"]],
    "OfferCancel": ["OfferSequence"],
    "SignerListSet": ["SignerQuorum"],
    "CheckCreate": ["Destination", ["IssuedSendMax", "SendMax"]],
    "CheckCancel": ["CheckID"],
    "CheckCash": [
        "CheckID",
        ["Amount", "IssuedAmount", "DeliverMin", "IssuedDeliverMin"],
    ],
    "DepositPreauth": [["Authorize", "Unauthorize"]],
    "AccountDelete": ["Destination"],
}

AMOUNT_FIELDS = ["Amount", "DeliverMin", "SendMax", "TakerGets", "TakerPays"]

REQUIRED_PAYMENT_FIELDS = ("Amount", "Destination")


@expect(messages.RippleAddress, field="address")
def get_address(client, address_n, show_display=False):
    return client.call(
        messages.RippleGetAddress(address_n=address_n, show_display=show_display)
    )


@expect(messages.RippleSignedTx)
def sign_tx(client, address_n, msg: messages.RippleSignTx):
    msg.address_n = address_n
    return client.call(msg)


@expect(messages.RipplePublicKey, field="public_key")
def get_public_key(client, address_n, show_display=False):
    return client.call(
        messages.RippleGetPublicKey(address_n=address_n, show_display=show_display)
    )


def create_sign_tx_msg(transaction) -> messages.RippleSignTx:
    check_fields(transaction, REQUIRED_FIELDS["Common"])
    prepare_amount_fields(transaction)

    if transaction["TransactionType"] not in transaction:
        check_fields(transaction, REQUIRED_FIELDS[transaction["TransactionType"]])
    else:
        check_fields(
            transaction.get(transaction["TransactionType"]),
            REQUIRED_FIELDS[transaction["TransactionType"]],
        )

    converted = dict_from_camelcase(transaction)
    return dict_to_proto(messages.RippleSignTx, converted)


def check_fields(msg, fields):
    """
    Checks for the existence of fields in the message.
    :param fields: List of required fields in `msg`, if one of multiple is required, provide as inner list
    """
    for field in fields:
        has_field = False
        if isinstance(field, list):
            for alternative in field:
                if alternative in msg:
                    has_field = True
                    break
        else:
            if field in msg:
                has_field = True
        if not has_field:
            raise ValueError(
                "Some of the following fields are missing {}".format(fields)
            )


def prepare_amount_fields(transaction):
    """
    Adds an 'Issued' prefix to every amount field containing an issued currency.
    :param transaction: A standard XRP transaction JSON
    """
    for k, v in transaction.items():
        if k in AMOUNT_FIELDS:
            if isinstance(v, dict):
                transaction["Issued" + k] = v
                del transaction[k]
