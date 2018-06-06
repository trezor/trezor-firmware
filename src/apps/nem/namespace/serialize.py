from trezor.messages.NEMProvisionNamespace import NEMProvisionNamespace
from trezor.messages.NEMTransactionCommon import NEMTransactionCommon

from ..helpers import NEM_TRANSACTION_TYPE_PROVISION_NAMESPACE
from ..writers import write_bytes_with_length, write_common, write_uint32, write_uint64


def serialize_provision_namespace(common: NEMTransactionCommon, namespace: NEMProvisionNamespace, public_key: bytes) -> bytearray:
    tx = write_common(common,
                      bytearray(public_key),
                      NEM_TRANSACTION_TYPE_PROVISION_NAMESPACE)

    write_bytes_with_length(tx, bytearray(namespace.sink))
    write_uint64(tx, namespace.fee)
    write_bytes_with_length(tx, bytearray(namespace.namespace))
    if namespace.parent:
        write_bytes_with_length(tx, bytearray(namespace.parent))
    else:
        write_uint32(tx, 0xffffffff)

    return tx
