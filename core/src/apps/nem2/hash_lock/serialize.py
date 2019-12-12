from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2HashLockTransaction import NEM2HashLockTransaction

from ubinascii import unhexlify

from ..writers import (
    serialize_tx_common,
    get_common_message_size,
    serialize_embedded_tx_common,
    get_embedded_common_message_size
)
from apps.common.writers import (
    write_bytes,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le
)

def serialize_hash_lock(
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    hash_lock: asdfkkasdklfklaskldfklf,
    embedded=False
) -> bytearray:
    tx = bytearray()

    # Total size is the size of the common transaction properties
    # + the hash lock transaction specific properties
    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += get_hash_lock_body_size()

    # Write size
    write_uint32_le(tx, size)
    # Write the common properties
    tx = serialize_tx_common(tx, common)

    # Write the hash lock transaction body
    serialize_mosaic(tx, hash_lock.mosaic.id, hash_lock.mosaic.amount) # mosaic
    write_uint64_le(tx, int(hash_lock.duration)) # duration
    write_bytes(tx, unhexlify(hash_lock.hash)) # hash

    return tx

def get_hash_lock_body_size():
    # Add up the hash lock specific message attribute sizes
    size = 8 # mosaic ID is 8 bytes
    size += 8 # mosaic amount is 8 bytes
    size += 8 # duration is 8 bytes
    size += 32 # hash is 32 bytes
    return size

def serialize_mosaic(w: bytearray, mosaic_id: str, amount: int):
    write_uint64_le(w, int(mosaic_id, 16))
    write_uint64_le(w, int(amount))
