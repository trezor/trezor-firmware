from trezor.crypto import random
from trezor.messages.NEMImportanceTransfer import NEMImportanceTransfer
from trezor.messages.NEMMosaic import NEMMosaic
from trezor.messages.NEMTransactionCommon import NEMTransactionCommon
from trezor.messages.NEMTransfer import NEMTransfer

from ..helpers import (
    AES_BLOCK_SIZE,
    NEM_SALT_SIZE,
    NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER,
    NEM_TRANSACTION_TYPE_TRANSFER,
)
from ..writers import (
    serialize_tx_common,
    write_bytes_with_len,
    write_uint32_le,
    write_uint64_le,
)


def serialize_transfer(
    common: NEMTransactionCommon,
    transfer: NEMTransfer,
    public_key: bytes,
    payload: bytes = None,
    encrypted: bool = False,
) -> bytearray:
    tx = serialize_tx_common(
        common,
        public_key,
        NEM_TRANSACTION_TYPE_TRANSFER,
        _get_version(common.network, transfer.mosaics),
    )

    write_bytes_with_len(tx, transfer.recipient.encode())
    write_uint64_le(tx, transfer.amount)

    if payload:
        # payload + payload size (u32) + encryption flag (u32)
        write_uint32_le(tx, len(payload) + 2 * 4)
        if encrypted:
            write_uint32_le(tx, 0x02)
        else:
            write_uint32_le(tx, 0x01)
        write_bytes_with_len(tx, payload)
    else:
        write_uint32_le(tx, 0)

    if transfer.mosaics:
        write_uint32_le(tx, len(transfer.mosaics))

    return tx


def serialize_mosaic(w: bytearray, namespace: str, mosaic: str, quantity: int):
    identifier_w = bytearray()
    write_bytes_with_len(identifier_w, namespace.encode())
    write_bytes_with_len(identifier_w, mosaic.encode())

    mosaic_w = bytearray()
    write_bytes_with_len(mosaic_w, identifier_w)
    write_uint64_le(mosaic_w, quantity)

    write_bytes_with_len(w, mosaic_w)


def serialize_importance_transfer(
    common: NEMTransactionCommon, imp: NEMImportanceTransfer, public_key: bytes
) -> bytearray:
    w = serialize_tx_common(
        common, public_key, NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER
    )

    write_uint32_le(w, imp.mode)
    write_bytes_with_len(w, imp.public_key)
    return w


def get_transfer_payload(transfer: NEMTransfer, node) -> [bytes, bool]:
    payload = transfer.payload
    encrypted = False
    if transfer.public_key is not None:
        if payload is None:
            raise ValueError("Public key provided but no payload to encrypt")
        payload = _encrypt(node, transfer.public_key, transfer.payload)
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
    if not mosaics:
        return []
    ret = []
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
