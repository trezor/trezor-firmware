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

import json

from . import messages as proto
from .tools import CallException, expect

TYPE_TRANSACTION_TRANSFER = 0x4154
TYPE_MULTISIG_SIGNATURE = 0x1002
TYPE_MOSAIC_DEFINITION = 0x414D

NETWORK_TYPE_MIJIN_TEST = 0x90
NETWORK_TYPE_MIJIN = 0x60
NETWORK_TYPE_TEST_NET = 0x98
NETWORK_TYPE_MAIN_NET = 0x68

def create_transaction_common(transaction):
    msg = proto.NEM2TransactionCommon()
    msg.type = transaction["type"]
    msg.network_type = transaction["network_type"]
    msg.version = transaction["version"]
    msg.max_fee = transaction["max_fee"]
    msg.deadline = transaction["deadline"]

    if "signer" in transaction:
        msg.signer = bytes.fromhex(transaction["signer"])

    return msg


def create_transfer(transaction):
    msg = proto.NEM2TransferTransaction()
    msg.recipient_address = transaction["recipient_address"]

    if "payload" in transaction["message"]:
        msg.message = bytes.fromhex(transaction["message"]["payload"])

    if "mosaics" in transaction:
        msg.mosaics = [
            proto.NEM2Mosaic(
                id=int(mosaic["id"], 16),
                amount=mosaic["amount"],
            )
            for mosaic in transaction["mosaics"]
        ]

    return msg

def create_mosaic_defnition(transaction):
    msg = proto.NEM2MosaicDefinitionTransaction()
    msg.nonce = 2
    return msg

def fill_transaction_by_type(msg, transaction):
    if transaction["type"] == TYPE_TRANSACTION_TRANSFER:
        msg.transfer = create_transfer(transaction)
    if transaction["type"] == TYPE_MOSAIC_DEFINITION:
        msg.mosaic_definition = create_mosaic_defnition(transaction)
    else:
        raise ValueError("Unknown transaction type")


def create_sign_tx(transaction):
    msg = proto.NEM2SignTx()
    msg.transaction = create_transaction_common(transaction)

    fill_transaction_by_type(msg, transaction)

    return msg


# ====== Client functions ====== #


@expect(proto.NEMAddress, field="address")
def get_address(client, n, network, show_display=False):
    return client.call(
        proto.NEMGetAddress(address_n=n, network=network, show_display=show_display)
    )


@expect(proto.NEM2SignedTx)
def sign_tx(client, n, transaction):
    try:
        msg = create_sign_tx(transaction)
    except ValueError as e:
        raise CallException(e.args)

    assert msg.transaction is not None
    msg.address_n = n
    msg.generation_hash = int(transaction["generation_hash"], 16)
    return client.call(msg)
