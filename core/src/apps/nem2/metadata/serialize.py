from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2NamespaceMetadataTransaction import NEM2NamespaceMetadataTransaction
from trezor.messages.NEM2MosaicMetadataTransaction import NEM2MosaicMetadataTransaction

from ubinascii import unhexlify

from ..helpers import (
    NEM2_TRANSACTION_TYPE_NAMESPACE_METADATA,
    NEM2_TRANSACTION_TYPE_MOSAIC_METADATA
)

from ..writers import (
    serialize_tx_common,
    get_common_message_size,
    serialize_embedded_tx_common,
    get_embedded_common_message_size
)
from apps.common.writers import (
    write_bytes,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le
)

def serialize_metadata(
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    metadata: NEM2NamespaceMetadataTransaction | NEM2NamespaceMetadataTransaction,
    embedded=False
) -> bytearray:
    tx = bytearray()

    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += metadata_body_size(metadata)

    write_uint32_le(tx, size)
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)
    write_bytes(tx, serialize_metadata_body(metadata, common.type))

    return tx

def metadata_body_size(metadata):
    # add up the metadata message attribute sizes
    size = 32 # target public key
    size += 8 # scoped metadata key
    size += 8 # target namespace/mosaic id
    size += 2 # value size delta
    size += 2 # value size
    size += metadata.value_size
    return size

def serialize_metadata_body(
    metadata: NEM2NamespaceMetadataTransaction | NEM2NamespaceMetadataTransaction,
    entity_type: int
) -> bytearray:

    tx = bytearray()

    write_bytes(tx, unhexlify(metadata.target_public_key))

    write_uint64_le(tx, int(metadata.scoped_metadata_key, 16))

    if entity_type == NEM2_TRANSACTION_TYPE_NAMESPACE_METADATA:
        write_uint64_le(tx, int(metadata.target_namespace_id, 16))
    elif entity_type == NEM2_TRANSACTION_TYPE_MOSAIC_METADATA:
        write_uint64_le(tx, int(metadata.target_mosaic_id, 16))

    write_uint16_le(tx, metadata.value_size_delta)

    write_uint16_le(tx, metadata.value_size)

    write_bytes(tx, unhexlify(metadata.value))

    return tx