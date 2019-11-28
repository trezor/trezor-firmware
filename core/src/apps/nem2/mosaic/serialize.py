from trezor.messages.NEM2MosaicDefinitionTransaction import NEM2MosaicDefinitionTransaction
from trezor.messages.NEM2MosaicSupplyChangeTransaction import NEM2MosaicSupplyChangeTransaction
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon

from ..helpers import (
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
)
from ..writers import (
    serialize_tx_common,
    get_common_message_size,    
    write_uint32_le,
    write_uint32_be,
    write_uint64_le,
    write_uint8
)


def serialize_mosaic_definition(
    common: NEM2TransactionCommon, creation: NEM2MosaicDefinitionTransaction, public_key: bytes
):
    tx = bytearray()

    size = get_common_message_size()
    # add up the mosaic-definition specific message attribute sizes
    size += 4 # nonce is 4 bytes
    size += 8 # mosaic id is 8 bytes
    size += 1 # flags is 1 byte
    size += 1 # divisibility is 1 byte
    size += 8 # duration is 8 bytes

    write_uint32_le(tx, size)

    tx = serialize_tx_common(tx, common)

    write_uint32_le(tx, int(creation.mosaic_id[8:], 16))
    write_uint32_le(tx, int(creation.mosaic_id[:8], 16))
    write_uint64_le(tx, creation.duration)
    write_uint32_le(tx, creation.nonce)
    write_uint8(tx, creation.flags)
    write_uint8(tx, creation.divisibility)        

    return tx


def serialize_mosaic_supply(
    common: NEM2TransactionCommon, 
    supply_change: NEM2MosaicSupplyChangeTransaction
):
    tx = bytearray()

    size = get_common_message_size()
    # add up the mosaic-supply specific message attribute sizes
    size += 8 # mosaic id is 8 bytes
    size += 8 # delta
    size += 1 # action is 1 byte

    write_uint32_le(tx, size)

    tx = serialize_tx_common(tx, common)

    write_uint32_le(tx, int(supply_change.mosaic_id[8:], 16))
    write_uint32_le(tx, int(supply_change.mosaic_id[:8], 16))
    write_uint64_le(tx, supply_change.delta)    
    write_uint8(tx, supply_change.action)

    return tx
