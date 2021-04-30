from trezor.crypto import hashlib, nem
from trezor.messages import NEMAggregateModification, NEMTransactionCommon

from ..helpers import (
    NEM_TRANSACTION_TYPE_AGGREGATE_MODIFICATION,
    NEM_TRANSACTION_TYPE_MULTISIG,
    NEM_TRANSACTION_TYPE_MULTISIG_SIGNATURE,
)
from ..writers import serialize_tx_common, write_bytes_with_len, write_uint32_le


def serialize_multisig(common: NEMTransactionCommon, public_key: bytes, inner: bytes):
    w = serialize_tx_common(common, public_key, NEM_TRANSACTION_TYPE_MULTISIG)
    write_bytes_with_len(w, inner)
    return w


def serialize_multisig_signature(
    common: NEMTransactionCommon,
    public_key: bytes,
    inner: bytes,
    address_public_key: bytes,
):
    w = serialize_tx_common(common, public_key, NEM_TRANSACTION_TYPE_MULTISIG_SIGNATURE)
    digest = hashlib.sha3_256(inner, keccak=True).digest()
    address = nem.compute_address(address_public_key, common.network)

    write_uint32_le(w, 4 + len(digest))
    write_bytes_with_len(w, digest)
    write_bytes_with_len(w, address)
    return w


def serialize_aggregate_modification(
    common: NEMTransactionCommon, mod: NEMAggregateModification, public_key: bytes
):
    version = common.network << 24 | 1
    if mod.relative_change:
        version = common.network << 24 | 2

    w = serialize_tx_common(
        common, public_key, NEM_TRANSACTION_TYPE_AGGREGATE_MODIFICATION, version
    )
    write_uint32_le(w, len(mod.modifications))
    return w


def write_cosignatory_modification(
    w: bytearray, cosignatory_type: int, cosignatory_pubkey: bytes
):
    write_uint32_le(w, 4 + 4 + len(cosignatory_pubkey))
    write_uint32_le(w, cosignatory_type)
    write_bytes_with_len(w, cosignatory_pubkey)
    return w


def write_minimum_cosignatories(w: bytearray, relative_change: int):
    write_uint32_le(w, 4)
    write_uint32_le(w, relative_change)
