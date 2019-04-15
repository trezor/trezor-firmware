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

import json

from . import messages as proto
from .tools import CallException, expect

TYPE_TRANSACTION_TRANSFER = 0x0101
TYPE_IMPORTANCE_TRANSFER = 0x0801
TYPE_AGGREGATE_MODIFICATION = 0x1001
TYPE_MULTISIG_SIGNATURE = 0x1002
TYPE_MULTISIG = 0x1004
TYPE_PROVISION_NAMESPACE = 0x2001
TYPE_MOSAIC_CREATION = 0x4001
TYPE_MOSAIC_SUPPLY_CHANGE = 0x4002


def create_transaction_common(transaction):
    msg = proto.NEMTransactionCommon()
    msg.network = (transaction["version"] >> 24) & 0xFF
    msg.timestamp = transaction["timeStamp"]
    msg.fee = transaction["fee"]
    msg.deadline = transaction["deadline"]

    if "signer" in transaction:
        msg.signer = bytes.fromhex(transaction["signer"])

    return msg


def create_transfer(transaction):
    msg = proto.NEMTransfer()
    msg.recipient = transaction["recipient"]
    msg.amount = transaction["amount"]

    if "payload" in transaction["message"]:
        msg.payload = bytes.fromhex(transaction["message"]["payload"])

        if transaction["message"]["type"] == 0x02:
            msg.public_key = bytes.fromhex(transaction["message"]["publicKey"])

    if "mosaics" in transaction:
        msg.mosaics = [
            proto.NEMMosaic(
                namespace=mosaic["mosaicId"]["namespaceId"],
                mosaic=mosaic["mosaicId"]["name"],
                quantity=mosaic["quantity"],
            )
            for mosaic in transaction["mosaics"]
        ]

    return msg


def create_aggregate_modification(transactions):
    msg = proto.NEMAggregateModification()
    msg.modifications = [
        proto.NEMCosignatoryModification(
            type=modification["modificationType"],
            public_key=bytes.fromhex(modification["cosignatoryAccount"]),
        )
        for modification in transactions["modifications"]
    ]

    if "minCosignatories" in transactions:
        msg.relative_change = transactions["minCosignatories"]["relativeChange"]

    return msg


def create_provision_namespace(transaction):
    msg = proto.NEMProvisionNamespace()
    msg.namespace = transaction["newPart"]

    if transaction["parent"]:
        msg.parent = transaction["parent"]

    msg.sink = transaction["rentalFeeSink"]
    msg.fee = transaction["rentalFee"]
    return msg


def create_mosaic_creation(transaction):
    definition = transaction["mosaicDefinition"]
    msg = proto.NEMMosaicCreation()
    msg.definition = proto.NEMMosaicDefinition()
    msg.definition.namespace = definition["id"]["namespaceId"]
    msg.definition.mosaic = definition["id"]["name"]

    if definition["levy"]:
        msg.definition.levy = definition["levy"]["type"]
        msg.definition.fee = definition["levy"]["fee"]
        msg.definition.levy_address = definition["levy"]["recipient"]
        msg.definition.levy_namespace = definition["levy"]["mosaicId"]["namespaceId"]
        msg.definition.levy_mosaic = definition["levy"]["mosaicId"]["name"]

    msg.definition.description = definition["description"]

    for property in definition["properties"]:
        name = property["name"]
        value = json.loads(property["value"])

        if name == "divisibility":
            msg.definition.divisibility = value
        elif name == "initialSupply":
            msg.definition.supply = value
        elif name == "supplyMutable":
            msg.definition.mutable_supply = value
        elif name == "transferable":
            msg.definition.transferable = value

    msg.sink = transaction["creationFeeSink"]
    msg.fee = transaction["creationFee"]
    return msg


def create_supply_change(transaction):
    msg = proto.NEMMosaicSupplyChange()
    msg.namespace = transaction["mosaicId"]["namespaceId"]
    msg.mosaic = transaction["mosaicId"]["name"]
    msg.type = transaction["supplyType"]
    msg.delta = transaction["delta"]
    return msg


def create_importance_transfer(transaction):
    msg = proto.NEMImportanceTransfer()
    msg.mode = transaction["importanceTransfer"]["mode"]
    msg.public_key = bytes.fromhex(transaction["importanceTransfer"]["publicKey"])
    return msg


def fill_transaction_by_type(msg, transaction):
    if transaction["type"] == TYPE_TRANSACTION_TRANSFER:
        msg.transfer = create_transfer(transaction)
    elif transaction["type"] == TYPE_AGGREGATE_MODIFICATION:
        msg.aggregate_modification = create_aggregate_modification(transaction)
    elif transaction["type"] == TYPE_PROVISION_NAMESPACE:
        msg.provision_namespace = create_provision_namespace(transaction)
    elif transaction["type"] == TYPE_MOSAIC_CREATION:
        msg.mosaic_creation = create_mosaic_creation(transaction)
    elif transaction["type"] == TYPE_MOSAIC_SUPPLY_CHANGE:
        msg.supply_change = create_supply_change(transaction)
    elif transaction["type"] == TYPE_IMPORTANCE_TRANSFER:
        msg.importance_transfer = create_importance_transfer(transaction)
    else:
        raise ValueError("Unknown transaction type")


def create_sign_tx(transaction):
    msg = proto.NEMSignTx()
    msg.transaction = create_transaction_common(transaction)
    msg.cosigning = transaction["type"] == TYPE_MULTISIG_SIGNATURE

    if transaction["type"] in (TYPE_MULTISIG_SIGNATURE, TYPE_MULTISIG):
        other_trans = transaction["otherTrans"]
        msg.multisig = create_transaction_common(other_trans)
        fill_transaction_by_type(msg, other_trans)
    elif "otherTrans" in transaction:
        raise ValueError("Transaction does not support inner transaction")
    else:
        fill_transaction_by_type(msg, transaction)

    return msg


# ====== Client functions ====== #


@expect(proto.NEMAddress, field="address")
def get_address(client, n, network, show_display=False):
    return client.call(
        proto.NEMGetAddress(address_n=n, network=network, show_display=show_display)
    )


@expect(proto.NEMSignedTx)
def sign_tx(client, n, transaction):
    try:
        msg = create_sign_tx(transaction)
    except ValueError as e:
        raise CallException(e.args)

    assert msg.transaction is not None
    msg.transaction.address_n = n
    return client.call(msg)
