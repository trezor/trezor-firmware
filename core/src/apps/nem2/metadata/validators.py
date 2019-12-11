from trezor.messages.NEM2SignTx import (
    NEM2SignTx,
    NEM2AddressAliasTransaction
)

from trezor.wire import ProcessError

def _validate_namespace_metadata(namespace_metadata: NEM2NamespaceMetadataTransaction, version: int):

    # https://nemtech.github.io/concepts/metadata.html#namespace-metadata-transaction

    if(namespace_metadata.target_public_key is None):
        raise ProcessError("Invalid target public key")

    if(namespace_metadata.scoped_metadata_key is None):
        raise ProcessError("Invalid scoped metadata key")

    if(namespace_metadata.target_namespace_id is None):
        raise ProcessError("Invalid target namespace id")

    if(namespace_metadata.value_size_delta is None):
        raise ProcessError("Invalid value size delta")

    if(namespace_metadata.value_size is None ):
        raise ProcessError("Invalid value size, value size not provided")

    if(namespace_metadata.value_size > 1024 ):
        raise ProcessError("Invalid value size, value size cannot be greater than 1024")

    if(namespace_metadata.value is None):
        raise ProcessError("Invalid value")



