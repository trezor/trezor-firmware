from .writers import *
from apps.nem.layout import *


async def ask_provision_namespace(ctx, msg: NEMSignTx):
    if msg.provision_namespace.parent:
        await require_confirm_action(ctx, 'Create namespace "' + msg.provision_namespace.namespace + '"' +
                                     'under namespace "' + msg.provision_namespace.parent + '"?')
    else:
        await require_confirm_action(ctx, 'Create namespace "' + msg.provision_namespace.namespace + '"?')
    await require_confirm_fee(ctx, 'Confirm rental fee', msg.provision_namespace.fee)

    await require_confirm_final(ctx, msg.transaction.fee)


def serialize_provision_namespace(msg: NEMSignTx, public_key: bytes) -> bytearray:
    tx = write_common(msg.transaction,
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
