from apps.nem.writers import *
from apps.nem.helpers import *
from trezor.messages.NEMMosaic import NEMMosaic
from trezor.messages.NEMSignTx import NEMSignTx
from trezor.crypto import random


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


def serialize_mosaic(w: bytearray, namespace: str, mosaic: str, quantity: int):
    identifier_length = 4 + len(namespace) + 4 + len(mosaic)
    # indentifier length (u32) + quantity (u64) + identifier size
    write_uint32(w, 4 + 8 + identifier_length)
    write_uint32(w, identifier_length)
    write_bytes_with_length(w, bytearray(namespace))
    write_bytes_with_length(w, bytearray(mosaic))
    write_uint64(w, quantity)


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


def canonicalize_mosaics(mosaics: list):
    if len(mosaics) <= 1:
        return mosaics
    mosaics = merge_mosaics(mosaics)
    return sort_mosaics(mosaics)


def are_mosaics_equal(a: NEMMosaic, b: NEMMosaic) -> bool:
    if a.namespace == b.namespace and a.mosaic == b.mosaic:
        return True
    return False


def merge_mosaics(mosaics: list) -> list:
    if not len(mosaics):
        return list()
    ret = list()
    for i in mosaics:
        found = False
        for k, y in enumerate(ret):
            if are_mosaics_equal(i, y):
                ret[k].quantity += i.quantity
                found = True
        if not found:
            ret.append(i)
    return ret


def sort_mosaics(mosaics: list) -> list:
    return sorted(mosaics, key=lambda m: (m.namespace, m.mosaic))
