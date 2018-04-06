from .writers import *
from apps.nem.layout import *
from trezor.messages import NEMImportanceTransferMode
from trezor.crypto import random


async def ask_transfer(ctx, msg: NEMSignTx, payload, encrypted):
    if payload:
        await require_confirm_payload(ctx, msg.transfer.payload, encrypted)

    for mosaic in msg.transfer.mosaics:
        await require_confirm_action(ctx, 'Confirm transfer of ' + str(mosaic.quantity) +
                                     ' raw units of ' + mosaic.namespace + '.' + mosaic.mosaic)

    await require_confirm_transfer(ctx, msg.transfer.recipient, msg.transfer.amount)

    await require_confirm_final(ctx, msg.transaction.fee)


async def ask_importance_transfer(ctx, msg: NEMSignTx):
    if msg.importance_transfer.mode == NEMImportanceTransferMode.ImportanceTransfer_Activate:
        m = 'Activate'
    else:
        m = 'Deactivate'
    await require_confirm_action(ctx, m + ' remote harvesting?')
    await require_confirm_final(ctx, msg.transaction.fee)


def serialize_transfer(msg: NEMSignTx, public_key: bytes, payload: bytes=None, encrypted: bool=False) -> bytearray:
    tx = write_common(msg.transaction,
                      bytearray(public_key),
                      NEM_TRANSACTION_TYPE_TRANSFER,
                      _get_version(msg.transaction.network, msg.transfer.mosaics))

    write_bytes_with_length(tx, bytearray(msg.transfer.recipient))
    write_uint64(tx, msg.transfer.amount)

    if payload:
        # payload + payload size (u32) + encryption flag (u32)
        write_uint32(tx, len(payload) + 2 * 4)
        if encrypted:
            write_uint32(tx, 0x02)
        else:
            write_uint32(tx, 0x01)
        write_bytes_with_length(tx, bytearray(payload))
    else:
        write_uint32(tx, 0)

    if msg.transfer.mosaics:
        write_uint32(tx, len(msg.transfer.mosaics))

    return tx


def serialize_importance_transfer(msg: NEMSignTx, public_key: bytes) -> bytearray:
    w = write_common(msg.transaction, bytearray(public_key), NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER)

    write_uint32(w, msg.importance_transfer.mode)
    write_bytes_with_length(w, bytearray(msg.importance_transfer.public_key))
    return w


def get_transfer_payload(msg: NEMSignTx, node) -> [bytes, bool]:
    payload = msg.transfer.payload
    encrypted = False
    if msg.transfer.public_key is not None:
        if payload is None:
            raise ValueError("Public key provided but no payload to encrypt")
        payload = _encrypt(node, msg.transfer.public_key, msg.transfer.payload)
        encrypted = True

    return payload, encrypted


def _encrypt(node, public_key: bytes, payload: bytes) -> bytes:
    salt = random.bytes(NEM_SALT_SIZE)
    iv = random.bytes(AES_BLOCK_SIZE)
    encrypted = node.nem_encrypt(public_key, iv, salt, payload)
    return iv + salt + encrypted


def _get_version(network, mosaics=None) -> int:
    if mosaics:
        return network << 24 | 2
    return network << 24 | 1
