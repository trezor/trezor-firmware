from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2AggregateTransaction import NEM2AggregateTransaction
from trezor.messages.NEM2InnerTransaction import NEM2InnerTransaction
from ubinascii import unhexlify
from trezor.crypto.hashlib import sha3_256
from trezor.utils import HashWriter

from ..helpers import (
    NEM2_TRANSACTION_TYPE_TRANSFER,
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
    NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS,
)

from ..writers import (
    serialize_tx_common,
    get_common_message_size,
    write_uint16_le,
    write_uint32_le,
    write_uint32_be,
    write_uint64_le,
    write_uint8,
    write_bytes
)

from ..transfer.serialize import serialize_transfer
from ..mosaic.serialize import serialize_mosaic_definition, serialize_mosaic_supply
from ..namespace.serialize import serialize_namespace_registration, serialize_address_alias
from .helpers import MerkleTools

def serialize_according_to_type(transaction):
    tx_type = transaction.common.type
    if tx_type == NEM2_TRANSACTION_TYPE_TRANSFER:
        return serialize_transfer(transaction.common, transaction.transfer, embedded=True)
    elif tx_type == NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION:
        return serialize_mosaic_definition(transaction.common, transaction.mosaic_definition, embedded=True)
    elif tx_type == NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION:
        return serialize_namespace_registration(transaction.common, transaction.namespace_registration, embedded=True)
    elif tx_type == NEM2_TRANSACTION_TYPE_ADDRESS_ALIAS:
        return serialize_address_alias(transaction.common, transaction.address_alias, embedded=True)

# 1. Takes in a list of non-serialized transactions
# 2. Serializes them as embedded transactions
# 3. Hash the serialized transactions
# 4. Add them to a merkle tree
# 5. Calcualte the root hash of the merkle tree and return
def compute_inner_transaction_hash(
    transactions: NEM2InnerTransactions
):
    mt = MerkleTools()

    for transaction in transactions:
        serialized_transaction = serialize_according_to_type(transaction)
        h = HashWriter(sha3_256())
        h.extend(serialized_transaction)
        mt.add_leaf(h.get_digest())

    mt.make_tree()
    return unhexlify(mt.get_merkle_root())

def getInnerTransactionPaddingSize(size, alignment):
        if (0 == size % alignment):
            return 0
        return alignment - (size % alignment)

def serialize_inner_transactions(
    inner_transactions: NEM2InnerTransactions
):
    txs = bytearray()
    for transaction in inner_transactions:
        serialized_transaction = serialize_according_to_type(transaction)
        inner_transaction_padding = getInnerTransactionPaddingSize(len(serialized_transaction), 8)
        write_bytes(txs, serialized_transaction)
        for _ in range(inner_transaction_padding):
            write_uint8(txs, 0)
    return txs

def serialize_aggregate_transaction_body(
    inner_transaction_hash,
    serialized_inner_transactions,
    cosignatures = bytearray()
):
    tx_body = bytearray()
    # Inner transaction hash bytes
    write_bytes(tx_body, inner_transaction_hash)
    # The payload size bytes
    write_uint32_le(tx_body, len(serialized_inner_transactions))
    # Reserved bytes
    write_uint32_le(tx_body, 0)
    # Transactions
    write_bytes(tx_body, serialized_inner_transactions)
    # Cosignatures
    #TODO
    write_bytes(tx_body, cosignatures)
    return tx_body

def serialize_aggregate_transaction(
    common: NEM2TransactionCommon,
    aggregate: NEM2AggregateTransaction
):
    tx = bytearray()

    # Transactions hash
    inner_transaction_hash = compute_inner_transaction_hash(aggregate.inner_transactions)
    # Serialize the inner trascations
    serialized_inner_transactions = serialize_inner_transactions(aggregate.inner_transactions)
    # Serialize the cosignatures
    # TODO
    # Serialize the body
    serialized_body = serialize_aggregate_transaction_body(inner_transaction_hash, serialized_inner_transactions)

    # Total size is the size of the common transaction properties
    # + the length of the serialized aggregate body
    size = get_common_message_size()
    size += len(serialized_body)
    # Write size
    write_uint32_le(tx, size)
    # Write the common properties
    tx = serialize_tx_common(tx, common)
    # Write the aggregate transaction body
    write_bytes(tx, serialized_body)

    return tx
