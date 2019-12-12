from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2AggregateTransaction import NEM2AggregateTransaction
from trezor.messages.NEM2InnerTransaction import NEM2InnerTransaction
from trezor.messages.NEM2Cosignature import NEM2Cosignature

from ubinascii import unhexlify
from trezor.crypto.hashlib import sha3_256
from trezor.utils import HashWriter

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

from .helpers import MerkleTools, map_type_to_property, map_type_to_serialize

def serialize_according_to_type(transaction):
    tx_type = transaction.common.type
    transaction_type_key = map_type_to_property[tx_type]
    serialize_function = map_type_to_serialize[tx_type]

    return serialize_function(
        transaction.common,
        transaction.__dict__[transaction_type_key],
        embedded=True)

# 1. Takes in a list of non-serialized transactions
# 2. Serializes them as embedded transactions
# 3. Hash the serialized transactions
# 4. Add them to a merkle tree
# 5. Calcualte the root hash of the merkle tree and return
def compute_inner_transaction_hash(
    transactions: NEM2InnerTransaction
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
    inner_transactions: NEM2InnerTransaction
):
    txs = bytearray()
    for transaction in inner_transactions:
        serialized_transaction = serialize_according_to_type(transaction)
        inner_transaction_padding = getInnerTransactionPaddingSize(len(serialized_transaction), 8)
        write_bytes(txs, serialized_transaction)
        for _ in range(inner_transaction_padding):
            write_uint8(txs, 0)
    return txs

def serialize_cosignatures(
    cosignatures: NEM2Cosignature
):
    txs = bytearray()
    for cosignature in cosignatures:
        write_bytes(txs, unhexlify(cosignature.public_key))
        write_bytes(txs, unhexlify(cosignature.signature))

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
    serialized_cosignatures = serialize_cosignatures(aggregate.cosignatures)
    # Serialize the body
    serialized_body = serialize_aggregate_transaction_body(inner_transaction_hash, serialized_inner_transactions, serialized_cosignatures)

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
