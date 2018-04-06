from .writers import *
from apps.nem.layout import *
from trezor.crypto import hashlib
from trezor.messages import NEMModificationType
from trezor.crypto import nem


async def ask_multisig(ctx, msg: NEMSignTx):
    # todo
    await require_confirm_action(ctx, 'Multisig?')


async def ask_aggregate_modification(ctx, msg: NEMSignTx):
    if not msg.multisig:
        await require_confirm_action(ctx, 'Convert account to multisig account?')

    for m in msg.aggregate_modification.modifications:
        if m.type == NEMModificationType.CosignatoryModification_Add:
            action = 'Add'
        else:
            action = 'Remove'
        address = nem.compute_address(m.public_key, msg.transaction.network)
        await require_confirm_address(ctx, action + ' cosignatory?', address)

    if msg.aggregate_modification.relative_change:
        if not msg.multisig:
            action = 'Set minimum cosignatories to '
        else:
            action = 'Modify the number of cosignatories by '
        await require_confirm_action(ctx, action + str(msg.aggregate_modification.relative_change) + '?')

    await require_confirm_final(ctx, msg.transaction.fee)


def serialize_multisig(msg: NEMTransactionCommon, public_key: bytes, inner: bytes):
    w = write_common(msg, bytearray(public_key), NEM_TRANSACTION_TYPE_MULTISIG)
    write_bytes_with_length(w, bytearray(inner))
    return w


def serialize_multisig_signature(msg: NEMTransactionCommon, public_key: bytes, inner: bytes, address: str):
    w = write_common(msg, bytearray(public_key), NEM_TRANSACTION_TYPE_MULTISIG_SIGNATURE)
    digest = hashlib.sha3_256(inner).digest(True)

    write_uint32(w, 4 + len(digest))
    write_bytes_with_length(w, digest)
    write_bytes_with_length(w, address)
    return w


def serialize_aggregate_modification(msg: NEMSignTx, public_key: bytes):
    version = msg.transaction.network << 24 | 1
    if msg.aggregate_modification.relative_change:
        version = msg.transaction.network << 24 | 2

    w = write_common(msg.transaction,
                     bytearray(public_key),
                     NEM_TRANSACTION_TYPE_AGGREGATE_MODIFICATION,
                     version)
    write_uint32(w, len(msg.aggregate_modification.modifications))
    return w


def serialize_cosignatory_modification(w: bytearray, type: int, cosignatory_pubkey: bytes):
    write_uint32(w, 4 + 4 + len(cosignatory_pubkey))
    write_uint32(w, type)
    write_bytes_with_length(w, bytearray(cosignatory_pubkey))
    return w


def serialize_minimum_cosignatories(w: bytearray, relative_change: int):
    write_uint32(w, 4)
    write_uint32(w, relative_change)
