from trezor.crypto import random
from trezor.messages.NEMTransactionCommon import NEMTransactionCommon
from trezor.messages.NEMTransfer import NEMTransfer

from ..helpers import (
    AES_BLOCK_SIZE,
    NEM_TRANSACTION_TYPE_TRANSFER,
)
from ..writers import (
    serialize_tx_common,
    write_bytes_with_len,
    write_uint32_le,
    write_uint64_le,
)


def serialize_transfer(
    common: NEM2TransactionCommon,
    transfer: NEM2TransferTransaction,
    public_key: bytes,
    payload: bytes = None,
    encrypted: bool = False,
) -> bytearray:
    tx = serialize_tx_common(
        common,
        public_key,
        NEM_TRANSACTION_TYPE_TRANSFER,
        _get_version(common.network_type, transfer.mosaics),
    )

    write_bytes_with_len(tx, transfer.recipient_address.encode())

    if transfer.mosaics:
        write_uint32_le(tx, len(transfer.mosaics))

    return tx


def serialize_mosaic(w: bytearray, mosaic_id: int, amount: int):
    identifier_w = bytearray()
    write_uint64_le(identifier_w, mosaic_id)

    mosaic_w = bytearray()
    write_bytes_with_len(mosaic_w, identifier_w)
    write_uint64_le(mosaic_w, amount)

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


def get_transfer_payload(transfer: NEM2Transfer, node) -> [bytes, bool]:
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


def are_mosaics_equal(a: NEM2Mosaic, b: NEM2Mosaic) -> bool:
    if a.id == b.id:
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
                ret[k].amount += i.amount
                found = True
        if not found:
            ret.append(i)
    return ret


def sort_mosaics(mosaics: list) -> list:
    return sorted(mosaics, key=lambda m: (m.namespace, m.mosaic))
