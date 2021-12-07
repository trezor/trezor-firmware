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

import json
from typing import TYPE_CHECKING

from . import exceptions, messages
from .tools import expect

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address
    from .protobuf import MessageType

TYPE_TRANSACTION_TRANSFER = 0x0101
TYPE_IMPORTANCE_TRANSFER = 0x0801
TYPE_AGGREGATE_MODIFICATION = 0x1001
TYPE_MULTISIG_SIGNATURE = 0x1002
TYPE_MULTISIG = 0x1004
TYPE_PROVISION_NAMESPACE = 0x2001
TYPE_MOSAIC_CREATION = 0x4001
TYPE_MOSAIC_SUPPLY_CHANGE = 0x4002


def create_transaction_common(transaction: dict) -> messages.NEMTransactionCommon:
    msg = messages.NEMTransactionCommon()
    msg.network = (transaction["version"] >> 24) & 0xFF
    msg.timestamp = transaction["timeStamp"]
    msg.fee = transaction["fee"]
    msg.deadline = transaction["deadline"]

    if "signer" in transaction:
        msg.signer = bytes.fromhex(transaction["signer"])

    return msg


def create_transfer(transaction: dict) -> messages.NEMTransfer:
    msg = messages.NEMTransfer()
    msg.recipient = transaction["recipient"]
    msg.amount = transaction["amount"]

    if "payload" in transaction["message"]:
        msg.payload = bytes.fromhex(transaction["message"]["payload"])

        if transaction["message"]["type"] == 0x02:
            msg.public_key = bytes.fromhex(transaction["message"]["publicKey"])

    if "mosaics" in transaction:
        msg.mosaics = [
            messages.NEMMosaic(
                namespace=mosaic["mosaicId"]["namespaceId"],
                mosaic=mosaic["mosaicId"]["name"],
                quantity=mosaic["quantity"],
            )
            for mosaic in transaction["mosaics"]
        ]

    return msg


def create_aggregate_modification(
    transaction: dict,
) -> messages.NEMAggregateModification:
    msg = messages.NEMAggregateModification()
    msg.modifications = [
        messages.NEMCosignatoryModification(
            type=modification["modificationType"],
            public_key=bytes.fromhex(modification["cosignatoryAccount"]),
        )
        for modification in transaction["modifications"]
    ]

    if "minCosignatories" in transaction:
        msg.relative_change = transaction["minCosignatories"]["relativeChange"]

    return msg


def create_provision_namespace(transaction: dict) -> messages.NEMProvisionNamespace:
    msg = messages.NEMProvisionNamespace()
    msg.namespace = transaction["newPart"]

    if transaction["parent"]:
        msg.parent = transaction["parent"]

    msg.sink = transaction["rentalFeeSink"]
    msg.fee = transaction["rentalFee"]
    return msg


def create_mosaic_creation(transaction: dict) -> messages.NEMMosaicCreation:
    definition = transaction["mosaicDefinition"]
    msg = messages.NEMMosaicCreation()
    msg.definition = messages.NEMMosaicDefinition()
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


def create_supply_change(transaction: dict) -> messages.NEMMosaicSupplyChange:
    msg = messages.NEMMosaicSupplyChange()
    msg.namespace = transaction["mosaicId"]["namespaceId"]
    msg.mosaic = transaction["mosaicId"]["name"]
    msg.type = transaction["supplyType"]
    msg.delta = transaction["delta"]
    return msg


def create_importance_transfer(transaction: dict) -> messages.NEMImportanceTransfer:
    msg = messages.NEMImportanceTransfer()
    msg.mode = transaction["importanceTransfer"]["mode"]
    msg.public_key = bytes.fromhex(transaction["importanceTransfer"]["publicKey"])
    return msg


def fill_transaction_by_type(msg: messages.NEMSignTx, transaction: dict) -> None:
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


def create_sign_tx(transaction: dict) -> messages.NEMSignTx:
    msg = messages.NEMSignTx()
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


@expect(messages.NEMAddress, field="address", ret_type=str)
def get_address(
    client: "TrezorClient", n: "Address", network: int, show_display: bool = False
) -> "MessageType":
    return client.call(
        messages.NEMGetAddress(address_n=n, network=network, show_display=show_display)
    )


@expect(messages.NEMSignedTx)
def sign_tx(client: "TrezorClient", n: "Address", transaction: dict) -> "MessageType":
    try:
        msg = create_sign_tx(transaction)
    except ValueError as e:
        raise exceptions.TrezorException("Failed to encode transaction") from e

    assert msg.transaction is not None
    msg.transaction.address_n = n
    return client.call(msg)
