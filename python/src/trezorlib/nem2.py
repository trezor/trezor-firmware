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
TYPE_MOSAIC_SUPPLY_CHANGE = 0x424D
TYPE_NAMESPACE_REGISTRATION = 0x414E

NAMESPACE_REGISTRATION_TYPE_ROOT = 0x00
NAMESPACE_REGISTRATION_TYPE_CHILD = 0x01

NETWORK_TYPE_MIJIN_TEST = 0x90
NETWORK_TYPE_MIJIN = 0x60
NETWORK_TYPE_TEST_NET = 0x98
NETWORK_TYPE_MAIN_NET = 0x68

def create_transaction_common(transaction):
    msg = proto.NEM2TransactionCommon()
    msg.type = transaction["type"]
    msg.network_type = transaction["network"]
    msg.version = transaction["version"]
    msg.max_fee = transaction["maxFee"]
    msg.deadline = transaction["deadline"]

    if "signer" in transaction:
        msg.signer = bytes.fromhex(transaction["signer"])

    return msg


def create_transfer(transaction):
    msg = proto.NEM2TransferTransaction()
    msg.recipient_address = proto.NEM2RecipientAddress(
        address=transaction["recipientAddress"]["address"],
        network_type=transaction["recipientAddress"]["networkType"],
    )

    if "payload" in transaction["message"]:
        msg.message = proto.NEM2TransferMessage(
            payload=transaction["message"]["payload"],
            type=transaction["message"]["type"]
        )

    if "mosaics" in transaction:
        msg.mosaics = [
            proto.NEM2Mosaic(
                id=mosaic["id"],
                amount=mosaic["amount"],
            )
            for mosaic in transaction["mosaics"]
        ]

    return msg

def create_mosaic_definition(transaction):
    msg = proto.NEM2MosaicDefinitionTransaction()
    msg.nonce = transaction["nonce"]
    msg.mosaic_id = transaction["mosaicId"]
    msg.flags = transaction["flags"]
    msg.divisibility = transaction["divisibility"]
    msg.duration = int(transaction["duration"])
    return msg


def create_mosaic_supply(transaction):
    msg = proto.NEM2MosaicSupplyChangeTransaction()
    msg.mosaic_id = transaction["mosaicId"]
    msg.delta = int(transaction["delta"])
    msg.action = transaction["action"]
    return msg

def create_namespace_registration(transaction):
    msg = proto.NEM2NamespaceRegistrationTransaction()
    msg.registration_type = transaction["registrationType"]
    if(msg.registration_type == NAMESPACE_REGISTRATION_TYPE_ROOT):
        msg.duration = int(transaction["duration"]) # cast in case payload represents uint64 in string format
    if(msg.registration_type == NAMESPACE_REGISTRATION_TYPE_CHILD):
        msg.parent_id = int(transaction["parentId"], 16) # cast in case payload represents uint64 in string format
    msg.id = int(transaction["id"], 16)
    msg.namespace_name = transaction["namespaceName"].encode()
    return msg

def fill_transaction_by_type(msg, transaction):
    if transaction["type"] == TYPE_TRANSACTION_TRANSFER:
        msg.transfer = create_transfer(transaction)
    if transaction["type"] == TYPE_MOSAIC_DEFINITION:
        msg.mosaic_definition = create_mosaic_definition(transaction)
    if transaction["type"] == TYPE_MOSAIC_SUPPLY_CHANGE:
        msg.mosaic_supply = create_mosaic_supply(transaction)
    if transaction["type"] == TYPE_NAMESPACE_REGISTRATION:
        msg.namespace_registration = create_namespace_registration(transaction)


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
def sign_tx(client, n, generation_hash, transaction):

    assert n is not None
    assert generation_hash is not None

    try:
        msg = create_sign_tx(transaction)
    except ValueError as e:
        raise CallException(e.args)

    assert msg.transaction is not None
    msg.address_n = n
    msg.generation_hash = generation_hash
    return client.call(msg)
