from apps.nem.helpers import *
from apps.nem.writers import *
from trezor.messages.NEMSignTx import NEMSignTx


def serialize_provision_namespace(msg: NEMSignTx, public_key: bytes) -> bytearray:
    common = msg.transaction
    if msg.multisig:
        common = msg.multisig
    tx = write_common(common,
                      bytearray(public_key),
                      NEM_TRANSACTION_TYPE_PROVISION_NAMESPACE)

    write_bytes_with_length(tx, bytearray(msg.provision_namespace.sink))
    write_uint64(tx, msg.provision_namespace.fee)
    write_bytes_with_length(tx, bytearray(msg.provision_namespace.namespace))
    if msg.provision_namespace.parent:
        write_bytes_with_length(tx, bytearray(msg.provision_namespace.parent))
    else:
        write_uint32(tx, 0xffffffff)

    return tx
