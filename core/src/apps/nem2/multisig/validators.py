from trezor.messages.NEM2SignTx import (
    NEM2SignTx,
    NEM2MultisigModificationTransaction
)

from trezor.wire import ProcessError

def _validate_multisig_modification(multisig_modification: NEM2MultisigModificationTransaction, version: int):

    # https://nemtech.github.io/concepts/metadata.html#namespace-metadata-transaction

    if(multisig_modification.target_public_key is None):
        raise ProcessError("Invalid target public key")

    if(multisig_modification.scoped_metadata_key is None):
        raise ProcessError("Invalid scoped metadata key")

    if(multisig_modification.target_namespace_id is None):
        raise ProcessError("Invalid target namespace id")

    if(multisig_modification.value_size_delta is None):
        raise ProcessError("Invalid value size delta")

    if(multisig_modification.value_size is None ):
        raise ProcessError("Invalid value size, value size not provided")

    if(multisig_modification.value_size > 1024 ):
        raise ProcessError("Invalid value size, value size cannot be greater than 1024")

    if(multisig_modification.value is None):
        raise ProcessError("Invalid value")



