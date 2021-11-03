from trezor.crypto import random
from trezor.messages import (
    NEMImportanceTransfer,
    NEMMosaic,
    NEMTransactionCommon,
    NEMTransfer,
)

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

if False:
    from trezor.crypto import bip32
    from trezor.utils import Writer


def serialize_transfer(
    common: NEMTransactionCommon,
    transfer: NEMTransfer,
    public_key: bytes,
    payload: bytes,
    is_encrypted: bool,
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
        if is_encrypted:
            write_uint32_le(tx, 0x02)
        else:
            write_uint32_le(tx, 0x01)
        write_bytes_with_len(tx, payload)
    else:
        write_uint32_le(tx, 0)

    if transfer.mosaics:
        write_uint32_le(tx, len(transfer.mosaics))

    return tx


def serialize_mosaic(w: Writer, namespace: str, mosaic: str, quantity: int) -> None:
    identifier_w = bytearray()
    write_bytes_with_len(identifier_w, namespace.encode())
    write_bytes_with_len(identifier_w, mosaic.encode())

    mosaic_w = bytearray()
    write_bytes_with_len(mosaic_w, identifier_w)
    write_uint64_le(mosaic_w, quantity)

    write_bytes_with_len(w, mosaic_w)


def serialize_importance_transfer(
    common: NEMTransactionCommon, imp: NEMImportanceTransfer, public_key: bytes
) -> bytes:
    w = serialize_tx_common(
        common, public_key, NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER
    )

    write_uint32_le(w, imp.mode)
    write_bytes_with_len(w, imp.public_key)
    return w


def get_transfer_payload(
    transfer: NEMTransfer, node: bip32.HDNode
) -> tuple[bytes, bool]:
    if transfer.public_key is not None:
        if not transfer.payload:
            raise ValueError("Public key provided but no payload to encrypt")
        encrypted_payload = _encrypt(node, transfer.public_key, transfer.payload)
        return encrypted_payload, True
    else:
        return transfer.payload, False


def _encrypt(node: bip32.HDNode, public_key: bytes, payload: bytes) -> bytes:
    salt = random.bytes(NEM_SALT_SIZE)
    iv = random.bytes(AES_BLOCK_SIZE)
    encrypted = node.nem_encrypt(public_key, iv, salt, payload)
    return iv + salt + encrypted


def _get_version(network: int, mosaics: list[NEMMosaic] | None = None) -> int:
    if mosaics:
        return network << 24 | 2
    return network << 24 | 1


def canonicalize_mosaics(mosaics: list[NEMMosaic]) -> list[NEMMosaic]:
    if len(mosaics) <= 1:
        return mosaics
    mosaics = merge_mosaics(mosaics)
    return sort_mosaics(mosaics)


def are_mosaics_equal(a: NEMMosaic, b: NEMMosaic) -> bool:
    if a.namespace == b.namespace and a.mosaic == b.mosaic:
        return True
    return False


def merge_mosaics(mosaics: list[NEMMosaic]) -> list[NEMMosaic]:
    if not mosaics:
        return []
    ret: list[NEMMosaic] = []
    for i in mosaics:
        found = False
        for k, y in enumerate(ret):
            if are_mosaics_equal(i, y):
                ret[k].quantity += i.quantity
                found = True
        if not found:
            ret.append(i)
    return ret


def sort_mosaics(mosaics: list[NEMMosaic]) -> list[NEMMosaic]:
    return sorted(mosaics, key=lambda m: (m.namespace, m.mosaic))
