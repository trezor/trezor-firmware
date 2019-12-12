from trezor.crypto import base32

from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction

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
# reflect the serialization used here:
# https://github.com/nemtech/nem2-sdk-typescript-javascript/blob/master/src/infrastructure/catbuffer/TransferTransactionBodyBuilder.ts#L120
def serialize_transfer(
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    transfer: NEM2TransferTransaction,
    embedded=False
) -> bytearray:
    tx = bytearray()

    # Total size is the size of the common transaction properties
    # + the transfer transaction specific properties
    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += get_transfer_body_size(transfer)

    # Write size
    write_uint32_le(tx, size)
    # Write the common properties
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)
    # Write the transfer transaction body
    write_bytes(tx, serialize_transfer_body(transfer))

    return tx

def serialize_transfer_body(
    transfer: NEM2TransferTransaction
) -> bytearray:
    tx = bytearray()

    # recipient_address (catbuffer UnresolvedAddress - 25 bits) base 32 encoded
    write_bytes(tx, base32.decode(transfer.recipient_address.address))

    # mosaics count (1 byte)
    write_uint8(tx, len(transfer.mosaics))

    # message size (1 byte for type + n bytes for message payload size)
    write_uint16_le(tx, 1 + len(transfer.message.payload.encode()))

    # transfer tx reserved bytes (4 bytes)
    write_uint32_le(tx, 0)

    # mosaics
    for mosaic in transfer.mosaics:
        serialize_mosaic(tx, mosaic.id, mosaic.amount)

    # message type (1 bytes)
    write_uint8(tx, transfer.message.type)

    #message payload (<message size> bytes)
    write_bytes(tx, transfer.message.payload.encode())

    return tx

def get_transfer_body_size(transfer):
    # Add up the transfer-specific message attribute sizes
    size = 25 # recipient_address (catbuffer UnresolvedAddress)
    size += 2 # message size
    size += 1 # mosaics count
    size += 1 + len(transfer.message.payload.encode()) # message type takes up 1 byte
    size += len(transfer.mosaics) * (8 + 8) # 8 bytes id + 8 bytes amount (catbuffer Mosaic)
    size += 4 # reserved bytes
    return size

def serialize_mosaic(w: bytearray, mosaic_id: str, amount: int):
    write_uint64_le(w, int(mosaic_id, 16))
    write_uint64_le(w, int(amount))
