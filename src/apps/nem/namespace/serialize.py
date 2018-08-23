from trezor.messages.NEMProvisionNamespace import NEMProvisionNamespace
from trezor.messages.NEMTransactionCommon import NEMTransactionCommon

from ..helpers import NEM_TRANSACTION_TYPE_PROVISION_NAMESPACE
from ..writers import (
    serialize_tx_common,
    write_bytes_with_len,
    write_uint32_le,
    write_uint64_le,
)


def serialize_provision_namespace(
    common: NEMTransactionCommon, namespace: NEMProvisionNamespace, public_key: bytes
) -> bytearray:
    tx = serialize_tx_common(
        common, public_key, NEM_TRANSACTION_TYPE_PROVISION_NAMESPACE
    )

    write_bytes_with_len(tx, namespace.sink.encode())
    write_uint64_le(tx, namespace.fee)
    write_bytes_with_len(tx, namespace.namespace.encode())
    if namespace.parent:
        write_bytes_with_len(tx, namespace.parent.encode())
    else:
        write_uint32_le(tx, 0xffffffff)

    return tx
