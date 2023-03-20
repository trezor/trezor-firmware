from typing import TYPE_CHECKING

from ..writers import serialize_tx_common, write_bytes_with_len, write_uint32_le

if TYPE_CHECKING:
    from trezor.messages import NEMAggregateModification, NEMTransactionCommon
    from trezor.utils import Writer


def serialize_multisig(
    common: NEMTransactionCommon, public_key: bytes, inner: bytes
) -> bytes:
    from ..helpers import NEM_TRANSACTION_TYPE_MULTISIG

    w = serialize_tx_common(common, public_key, NEM_TRANSACTION_TYPE_MULTISIG)
    write_bytes_with_len(w, inner)
    return w


def serialize_multisig_signature(
    common: NEMTransactionCommon,
    public_key: bytes,
    inner: bytes,
    address_public_key: bytes,
) -> bytes:
    from trezor.crypto import hashlib, nem

    from ..helpers import NEM_TRANSACTION_TYPE_MULTISIG_SIGNATURE

    w = serialize_tx_common(common, public_key, NEM_TRANSACTION_TYPE_MULTISIG_SIGNATURE)
    digest = hashlib.sha3_256(inner, keccak=True).digest()
    address = nem.compute_address(address_public_key, common.network)

    write_uint32_le(w, 4 + len(digest))
    write_bytes_with_len(w, digest)
    write_bytes_with_len(w, address.encode())
    return w


def serialize_aggregate_modification(
    common: NEMTransactionCommon, mod: NEMAggregateModification, public_key: bytes
) -> bytearray:
    from ..helpers import NEM_TRANSACTION_TYPE_AGGREGATE_MODIFICATION

    version = common.network << 24 | 1
    if mod.relative_change:
        version = common.network << 24 | 2

    w = serialize_tx_common(
        common, public_key, NEM_TRANSACTION_TYPE_AGGREGATE_MODIFICATION, version
    )
    write_uint32_le(w, len(mod.modifications))
    return w


def write_cosignatory_modification(
    w: Writer, cosignatory_type: int, cosignatory_pubkey: bytes
) -> None:
    write_uint32_le(w, 4 + 4 + len(cosignatory_pubkey))
    write_uint32_le(w, cosignatory_type)
    write_bytes_with_len(w, cosignatory_pubkey)


def write_minimum_cosignatories(w: Writer, relative_change: int) -> None:
    write_uint32_le(w, 4)
    write_uint32_le(w, relative_change)
