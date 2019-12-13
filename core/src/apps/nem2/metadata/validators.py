from trezor.messages.NEM2NamespaceMetadataTransaction import NEM2NamespaceMetadataTransaction
from trezor.messages.NEM2MosaicMetadataTransaction import NEM2MosaicMetadataTransaction

from ..helpers import (
    NEM2_TRANSACTION_TYPE_NAMESPACE_METADATA,
    NEM2_TRANSACTION_TYPE_MOSAIC_METADATA
)

from ubinascii import unhexlify

from trezor.wire import ProcessError

def _validate_metadata(
    metadata: NEM2NamespaceMetadataTransaction | NEM2MosaicMetadataTransaction,
    entity_type: int
):

    # https://nemtech.github.io/concepts/metadata.html#namespace-metadata-transaction
    # https://nemtech.github.io/concepts/metadata.html#mosaic-metadata-transaction

    if metadata.target_public_key is None:
        raise ProcessError("Invalid target public key")

    if metadata.scoped_metadata_key is None:
        raise ProcessError("Invalid scoped metadata key")

    if entity_type == NEM2_TRANSACTION_TYPE_NAMESPACE_METADATA:
        if metadata.target_namespace_id is None:
            raise ProcessError("Invalid target namespace id")

    elif entity_type == NEM2_TRANSACTION_TYPE_MOSAIC_METADATA:
        if metadata.target_mosaic_id is None:
            raise ProcessError("Invalid target mosaic id")

    if metadata.value_size_delta is None:
        raise ProcessError("Invalid value size delta")

    if metadata.value_size is None:
        raise ProcessError("Invalid value size, value size not provided")

    if metadata.value_size > 1024:
        raise ProcessError("Invalid value size, value size cannot be greater than 1024")

    if metadata.value is None:
        raise ProcessError("Invalid value")

    if len(unhexlify(metadata.value)) > 1024:
        raise ProcessError("The maximum value size is 1024")
