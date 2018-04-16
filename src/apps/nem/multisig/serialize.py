from apps.nem.writers import *
from apps.nem.helpers import *
from trezor.messages.NEMSignTx import NEMSignTx
from trezor.crypto import hashlib
from trezor.crypto import nem


def serialize_multisig(common: NEMTransactionCommon, public_key: bytes, inner: bytes):
    w = write_common(common, bytearray(public_key), NEM_TRANSACTION_TYPE_MULTISIG)
    write_bytes_with_length(w, bytearray(inner))
    return w


def serialize_multisig_signature(common: NEMTransactionCommon, public_key: bytes,
                                 inner: bytes, address_public_key: bytes):
    address = nem.compute_address(address_public_key, common.network)
    w = write_common(common, bytearray(public_key), NEM_TRANSACTION_TYPE_MULTISIG_SIGNATURE)
    digest = hashlib.sha3_256(inner).digest(True)

    write_uint32(w, 4 + len(digest))
    write_bytes_with_length(w, digest)
    write_bytes_with_length(w, address)
    return w


def serialize_aggregate_modification(msg: NEMSignTx, public_key: bytes):
    common = msg.transaction
    if msg.multisig:
        common = msg.multisig
    version = common.network << 24 | 1
    if msg.aggregate_modification.relative_change:
        version = common.network << 24 | 2

    w = write_common(common,
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
