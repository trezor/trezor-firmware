from trezor.crypto import random, base32
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2MultisigModificationTransaction import NEM2MultisigModificationTransaction
from ubinascii import hexlify, unhexlify

from ..helpers import NEM2_TRANSACTION_TYPE_MULTISIG_MODIFICATION, unsigned_32_bit_int_to_8_bit

from ..writers import (
    serialize_tx_common,
    get_common_message_size,
    serialize_embedded_tx_common,
    get_embedded_common_message_size
)
from apps.common.writers import (
    write_bytes,
    write_uint8,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le
)

def serialize_multisig_modification(
    common: NEM2TransactionCommon,
    multisig_modification: NEM2MultisigModificationTransaction,
    embedded=False
) -> bytearray:
    tx = bytearray()

    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += get_multisig_modification_body_size(multisig_modification)

    write_uint32_le(tx, size)
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)
    write_bytes(tx, serialize_multisig_modification_body(multisig_modification))

    return tx

def get_multisig_modification_body_size(multisig_modification: NEM2MultisigModificationTransaction):
    # add up the multisig modification message attribute sizes
    size = 1 # min removal delta
    size += 1 # min approval delta
    size += 1 # public key additions count
    size += 1 # public key removals count
    size += 4 # reserved padding
    size += len(multisig_modification.public_key_additions) * 32 # public key additions
    size += len(multisig_modification.public_key_deletions) * 32 # public key removals
    return size

def serialize_multisig_modification_body(multisig_modification: NEM2MultisigModificationTransaction) -> bytearray:

    tx = bytearray()

    write_uint8(tx, unsigned_32_bit_int_to_8_bit(multisig_modification.min_removal_delta, signed=False))

    write_uint8(tx, unsigned_32_bit_int_to_8_bit(multisig_modification.min_approval_delta, signed=False))

    write_uint8(tx, len(multisig_modification.public_key_additions))

    write_uint8(tx, len(multisig_modification.public_key_deletions))

    write_uint32_le(tx, 0) # reserved bytes

    for addition in multisig_modification.public_key_additions:
        write_bytes(tx, unhexlify(addition))

    for deletion in multisig_modification.public_key_deletions:
        write_bytes(tx, unhexlify(deletion))

    return tx