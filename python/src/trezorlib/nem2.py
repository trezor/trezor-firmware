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
TYPE_ADDRESS_ALIAS = 0x424E
TYPE_NAMESPACE_METADATA = 0x4344
TYPE_MOSAIC_METADATA = 0x4244
TYPE_ACCOUNT_METADATA = 0x4144
TYPE_MOSAIC_ALIAS = 0x434E
TYPE_HASH_LOCK = 0x4148
TYPE_SECRET_LOCK = 0x4152
TYPE_SECRET_PROOF = 0x4252
TYPE_MULTISIG_MODIFICATION = 0x4155
TYPE_ACCOUNT_ADDRESS_RESTRICTION = 0x4150
TYPE_ACCOUNT_MOSAIC_RESTRICTION = 0x4250
TYPE_ACCOUNT_OPERATION_RESTRICTION = 0x4350

NAMESPACE_REGISTRATION_TYPE_ROOT = 0x00
NAMESPACE_REGISTRATION_TYPE_CHILD = 0x01

ALIAS_ACTION_TYPE_LINK = 0x01
ALIAS_ACTION_TYPE_UNLINK = 0x00

MOSAIC_SUPPLY_CHANGE_ACTION_INCREASE = 0x01
MOSAIC_SUPPLY_CHANGE_ACTION_DECREASE = 0x00

SECRET_LOCK_SHA3_256 = 0x00
SECRET_LOCK_KECCAK_256 = 0x01
SECRET_LOCK_HASH_160 = 0x02
ECRET_LOCK_HASH_256 = 0x03

NETWORK_TYPE_MIJIN_TEST = 0x90
NETWORK_TYPE_MIJIN = 0x60
NETWORK_TYPE_TEST_NET = 0x98
NETWORK_TYPE_MAIN_NET = 0x68

ACCOUNT_RESTRICTION_ALLOW_INCOMING_ADDRESS = 0x01
ACCOUNT_RESTRICTION_ALLOW_MOSAIC = 0x02
ACCOUNT_RESTRICTION_ALLOW_INCOMING_TRANSACTION_TYPE = 0x04
ACCOUNT_RESTRICTION_ALLOW_OUTGOING_ADDRESS = 0x4001
ACCOUNT_RESTRICTION_ALLOW_OUTGOING_TRANSACTION_TYPE = 0x4004
ACCOUNT_RESTRICTION_BLOCK_INCOMING_ADDRESS = 0x8001
ACCOUNT_RESTRICTION_BLOCK_MOSAIC = 0x8002
ACCOUNT_RESTRICTION_BLOCK_INCOMING_TRANSACTION_TYPE = 0x8004
ACCOUNT_RESTRICTION_BLOCK_OUTGOING_ADDRESS = 0xC001
ACCOUNT_RESTRICTION_BLOCK_OUTGOING_TRANSACTION_TYPE = 0xC004

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

def create_embedded_transaction_common(transaction):
    msg = proto.NEM2EmbeddedTransactionCommon()
    msg.type = transaction["type"]
    msg.network_type = transaction["network"]
    msg.version = transaction["version"]
    msg.public_key = transaction["publicKey"]

    return msg

def create_transfer(transaction):
    msg = proto.NEM2TransferTransaction()
    msg.recipient_address = proto.NEM2Address(
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

def create_aggregate(aggregate_transaction):
    msg = proto.NEM2AggregateTransaction()
    # Generate inner transactions
    inner_transactions = []
    for transaction in aggregate_transaction["innerTransactions"]:
        inner_transaction = proto.NEM2InnerTransaction()
        inner_transaction.common = create_embedded_transaction_common(transaction)
        fill_transaction_by_type(inner_transaction, transaction)
        inner_transactions.append(inner_transaction)

    # Generate cosignatures
    cosignatures = []
    if "cosignatures" in aggregate_transaction:
        for signature in aggregate_transaction["cosignatures"]:
            cosignature = proto.NEM2Cosignature()
            cosignature.signature = signature["signature"]
            cosignature.public_key = signature["publicKey"]
            cosignatures.append(cosignature)

    msg.inner_transactions = inner_transactions
    msg.cosignatures = cosignatures
    return msg

def create_namespace_registration(transaction):
    msg = proto.NEM2NamespaceRegistrationTransaction()
    msg.registration_type = transaction["registrationType"]
    if(msg.registration_type == NAMESPACE_REGISTRATION_TYPE_ROOT):
        msg.duration = transaction["duration"] # cast in case payload represents uint64 in string format
    if(msg.registration_type == NAMESPACE_REGISTRATION_TYPE_CHILD):
        msg.parent_id = transaction["parentId"] # cast in case payload represents uint64 in string format
    msg.id = transaction["id"]
    msg.namespace_name = transaction["namespaceName"]
    return msg

def create_mosaic_alias(transaction):
    msg = proto.NEM2MosaicAliasTransaction()
    msg.namespace_id = transaction["namespaceId"]
    msg.mosaic_id = transaction["mosaicId"]
    msg.alias_action = transaction["aliasAction"]
    return msg

def create_address_alias(transaction):
    msg = proto.NEM2AddressAliasTransaction()
    msg.namespace_id = transaction["namespaceId"]
    msg.address = proto.NEM2Address(
        address=transaction["address"]["address"],
        network_type=transaction["address"]["networkType"],
    )
    msg.alias_action = transaction["aliasAction"]
    return msg

def create_namespace_metadata(transaction):
    msg = proto.NEM2NamespaceMetadataTransaction()
    msg.target_public_key = transaction["targetPublicKey"]
    msg.scoped_metadata_key = transaction["scopedMetadataKey"]
    msg.target_namespace_id = transaction["targetNamespaceId"]
    msg.value_size_delta = transaction["valueSizeDelta"]
    msg.value_size = transaction["valueSize"]
    msg.value = transaction["value"]
    return msg

def create_mosaic_metadata(transaction):
    msg = proto.NEM2MosaicMetadataTransaction()
    msg.target_public_key = transaction["targetPublicKey"]
    msg.scoped_metadata_key = transaction["scopedMetadataKey"]
    msg.target_mosaic_id = transaction["targetMosaicId"]
    msg.value_size_delta = transaction["valueSizeDelta"]
    msg.value_size = transaction["valueSize"]
    msg.value = transaction["value"]
    return msg

def create_account_metadata(transaction):
    msg = proto.NEM2AccountMetadataTransaction()
    msg.target_public_key = transaction["targetPublicKey"]
    msg.scoped_metadata_key = transaction["scopedMetadataKey"]
    msg.value_size_delta = transaction["valueSizeDelta"]
    msg.value_size = transaction["valueSize"]
    msg.value = transaction["value"]
    return msg

def create_hash_lock(transaction):
    msg = proto.NEM2HashLockTransaction()
    msg.mosaic = proto.NEM2Mosaic(
        id=transaction["mosaic"]["id"],
        amount=transaction["mosaic"]["amount"],
    )
    msg.duration = int(transaction["duration"])
    msg.hash = transaction["hash"]
    return msg

def create_secret_lock(transaction):
    msg = proto.NEM2SecretLockTransaction()
    msg.mosaic = proto.NEM2Mosaic(
        id=transaction["mosaic"]["id"],
        amount=transaction["mosaic"]["amount"],
    )
    msg.recipient_address = proto.NEM2Address(
        address=transaction["recipientAddress"]["address"],
        network_type=transaction["recipientAddress"]["networkType"],
    )
    msg.duration = int(transaction["duration"])
    msg.hash_algorithm = int(transaction["hashType"])
    msg.secret = transaction["secret"]
    return msg

def create_secret_proof(transaction):
    msg = proto.NEM2SecretProofTransaction()
    msg.recipient_address = proto.NEM2Address(
        address=transaction["recipientAddress"]["address"],
        network_type=transaction["recipientAddress"]["networkType"],
    )
    msg.proof = transaction["proof"]
    msg.hash_algorithm = int(transaction["hashType"])
    msg.secret = transaction["secret"]
    return msg

def create_mutlisig_modification(transaction):
    msg = proto.NEM2MultisigModificationTransaction()
    # the smallest protobuf integer size is 32 bits
    # nem2 catapult uses a signed 8 bit integer for minApprovalDelta and minRemovalDelta
    msg.min_approval_delta = transaction["minApprovalDelta"] & 0x000000ff
    msg.min_removal_delta = transaction["minRemovalDelta"] & 0x000000ff

    msg.public_key_additions = transaction["publicKeyAdditions"]
    msg.public_key_deletions = transaction["publicKeyDeletions"]
    return msg

def map_address(address_data):
    return proto.NEM2Address(
        address=address_data["address"],
        network_type=address_data["networkType"],
    )

def create_account_address_restriction(transaction):
    msg = proto.NEM2AccountAddressRestrictionTransaction()
    msg.restriction_type = transaction["restrictionType"]
    msg.restriction_additions = [map_address(a) for a in transaction["restrictionAdditions"]]
    msg.restriction_deletions = [map_address(a) for a in transaction["restrictionDeletions"]]

    return msg

def create_account_mosaic_restriction(transaction):
    msg = proto.NEM2AccountMosaicRestrictionTransaction()
    msg.restriction_type = transaction["restrictionType"]
    msg.restriction_additions = transaction["restrictionAdditions"]
    msg.restriction_deletions = transaction["restrictionDeletions"]

    return msg

def create_account_operation_restriction(transaction):
    msg = proto.NEM2AccountOperationRestrictionTransaction()
    msg.restriction_type = transaction["restrictionType"]
    msg.restriction_additions = transaction["restrictionAdditions"]
    msg.restriction_deletions = transaction["restrictionDeletions"]

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
    if transaction["type"] == TYPE_MOSAIC_ALIAS:
        msg.mosaic_alias = create_mosaic_alias(transaction)
    if transaction["type"] == TYPE_ADDRESS_ALIAS:
        msg.address_alias = create_address_alias(transaction)
    if transaction["type"] == TYPE_NAMESPACE_METADATA:
        msg.namespace_metadata = create_namespace_metadata(transaction)
    if transaction["type"] == TYPE_MOSAIC_METADATA:
        msg.mosaic_metadata = create_mosaic_metadata(transaction)
    if transaction["type"] == TYPE_ACCOUNT_METADATA:
        msg.account_metadata = create_account_metadata(transaction)
    if transaction["type"] == TYPE_HASH_LOCK:
        msg.hash_lock = create_hash_lock(transaction)
    if transaction["type"] == TYPE_SECRET_LOCK:
        msg.secret_lock = create_secret_lock(transaction)
    if transaction["type"] == TYPE_SECRET_PROOF:
        msg.secret_proof = create_secret_proof(transaction)
    if transaction["type"] == TYPE_MULTISIG_MODIFICATION:
        msg.multisig_modification = create_mutlisig_modification(transaction)
    if transaction["type"] == TYPE_ACCOUNT_ADDRESS_RESTRICTION:
        msg.account_address_restriction = create_account_address_restriction(transaction)
    if transaction["type"] == TYPE_ACCOUNT_MOSAIC_RESTRICTION:
        msg.account_mosaic_restriction = create_account_mosaic_restriction(transaction)
    if transaction["type"] == TYPE_ACCOUNT_OPERATION_RESTRICTION:
        msg.account_operation_restriction = create_account_operation_restriction(transaction)


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
