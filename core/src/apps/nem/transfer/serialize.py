from typing import TYPE_CHECKING

from ..writers import (
    serialize_tx_common,
    write_bytes_with_len,
    write_uint32_le,
    write_uint64_le,
)

if TYPE_CHECKING:
    from trezor.crypto import bip32
    from trezor.messages import (
        NEMImportanceTransfer,
        NEMMosaic,
        NEMTransactionCommon,
        NEMTransfer,
    )
    from trezor.utils import Writer


def serialize_transfer(
    common: NEMTransactionCommon,
    transfer: NEMTransfer,
    public_key: bytes,
    payload: bytes,
    encrypted: bool,
) -> bytearray:
    from ..helpers import NEM_TRANSACTION_TYPE_TRANSFER
    from ..writers import write_uint32_le

    version = common.network << 24 | 2 if transfer.mosaics else common.network << 24 | 1
    tx = serialize_tx_common(
        common,
        public_key,
        NEM_TRANSACTION_TYPE_TRANSFER,
        version,
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
    from ..helpers import NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER

    w = serialize_tx_common(
        common, public_key, NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER
    )

    write_uint32_le(w, imp.mode)
    write_bytes_with_len(w, imp.public_key)
    return w


def get_transfer_payload(
    transfer: NEMTransfer, node: bip32.HDNode
) -> tuple[bytes, bool]:
    from trezor.crypto import random

    from ..helpers import AES_BLOCK_SIZE, NEM_SALT_SIZE

    if transfer.public_key is not None:
        if not transfer.payload:
            raise ValueError("Public key provided but no payload to encrypt")

        # encrypt payload
        salt = random.bytes(NEM_SALT_SIZE)
        iv = random.bytes(AES_BLOCK_SIZE)
        encrypted = node.nem_encrypt(transfer.public_key, iv, salt, transfer.payload)
        encrypted_payload = iv + salt + encrypted

        return encrypted_payload, True
    else:
        return transfer.payload or b"", False


def canonicalize_mosaics(mosaics: list[NEMMosaic]) -> list[NEMMosaic]:
    if len(mosaics) <= 1:
        return mosaics
    mosaics = _merge_mosaics(mosaics)
    return sorted(mosaics, key=lambda m: (m.namespace, m.mosaic))


def _merge_mosaics(mosaics: list[NEMMosaic]) -> list[NEMMosaic]:
    if not mosaics:
        return []
    ret: list[NEMMosaic] = []
    for i in mosaics:
        found = False
        for k, y in enumerate(ret):
            # are_mosaics_equal
            if i.namespace == y.namespace and i.mosaic == y.mosaic:
                ret[k].quantity += i.quantity
                found = True
        if not found:
            ret.append(i)
    return ret
