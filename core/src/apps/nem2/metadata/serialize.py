from trezor.crypto import random, base32
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2NamespaceMetadataTransaction import NEM2NamespaceMetadataTransaction
from ubinascii import hexlify, unhexlify

from ..helpers import (
    AES_BLOCK_SIZE,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
    NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
    NEM2_NAMESPACE_REGISTRATION_TYPE_SUB
)

from ..writers import (
    serialize_tx_common,
    get_common_message_size,
    serialize_embedded_tx_common,
    get_embedded_common_message_size
)
from apps.common.writers import (
    write_bytes,
    write_uint8,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le
)

def serialize_namespace_metadata(
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    namespace_metadata: NEM2NamespaceMetadataTransaction,
    embedded=False
) -> bytearray:
    tx = bytearray()

    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += get_namespace_metadata_body_size(namespace_metadata)

    write_uint32_le(tx, size)
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)
    write_bytes(tx, serialize_namespace_metadata_body(namespace_metadata))

    return tx

def get_namespace_metadata_body_size(namespace_metadata):
    # add up the namespace metadata message attribute sizes
    size = 32 # target public key
    size += 8 # scoped metadata key
    size += 8 # target namespace id
    size += 2 # value size delta
    size += 2 # value size
    size += namespace_metadata.value_size
    return size

def serialize_namespace_metadata_body(namespace_metadata: NEM2NamespaceMetadataTransaction) -> bytearray:

    tx = bytearray()

    write_bytes(tx, unhexlify(namespace_metadata.target_public_key))

    write_uint64_le(tx, int(namespace_metadata.scoped_metadata_key, 16))

    write_uint64_le(tx, int(namespace_metadata.target_namespace_id, 16))

    write_uint16_le(tx, namespace_metadata.value_size_delta)

    write_uint16_le(tx, namespace_metadata.value_size)

    write_bytes(tx, unhexlify(namespace_metadata.value))

    return tx