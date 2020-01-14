from trezor.crypto import base32
from ubinascii import unhexlify

from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2MosaicGlobalRestrictionTransaction import NEM2MosaicGlobalRestrictionTransaction
from trezor.messages.NEM2MosaicAddressRestrictionTransaction import NEM2MosaicAddressRestrictionTransaction 

from ..writers import (
    serialize_tx_common,
    get_common_message_size,
    serialize_embedded_tx_common,
    get_embedded_common_message_size
)

from apps.common.writers import (
    write_bytes,
    write_uint8,
    write_uint32_le,
    write_uint64_le
)

def serialize_global_restriction(
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    global_restriction: NEM2MosaicGlobalRestrictionTransaction,
    embedded=False
) -> bytearray:
    tx = bytearray()
    entity_type = common.type

    # Total size is the size of the common transaction properties
    # + the global restriction properties
    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += 8 # mosaic id
    size += 8 # reference mosaic id
    size += 8 # restriction key
    size += 8 # previous restriction value
    size += 8 # new restriction value
    size += 1 # previous restriction type
    size += 1 # new restriction type

    # Write size
    write_uint32_le(tx, size)
    # Write the common properties
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)

    # Write mosaic id
    write_uint32_le(tx, int(global_restriction.mosaic_id[8:], 16))
    write_uint32_le(tx, int(global_restriction.mosaic_id[:8], 16))
    # Write reference mosaic id
    write_uint32_le(tx, int(global_restriction.reference_mosaic_id[8:], 16))
    write_uint32_le(tx, int(global_restriction.reference_mosaic_id[:8], 16))
    # Write restriction key
    write_uint32_le(tx, int(global_restriction.restriction_key[8:], 16))
    write_uint32_le(tx, int(global_restriction.restriction_key[:8], 16))
    # Write previous restriction value
    write_uint64_le(tx, int(global_restriction.previous_restriction_value))
    # Write new restriction value
    write_uint64_le(tx, int(global_restriction.new_restriction_value))
    # Write previous restriction type
    write_uint8(tx, global_restriction.previous_restriction_type)
    # Write new restriction type
    write_uint8(tx, global_restriction.new_restriction_type)

    return tx


def serialize_address_restriction(
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    address_restriction: NEM2MosaicAddressRestrictionTransaction,
    embedded=False
):
    tx = bytearray()
    entity_type = common.type

    # Total size is the size of the common transaction properties
    # + the address restriction properties
    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += 8 # mosaic id
    size += 8 # restriction key
    size += 8 # previous restriction value
    size += 8 # new restriction value
    size += 25 # target address

    # Write size
    write_uint32_le(tx, size)
    # Write the common properties
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)

    # Write mosaic id
    write_uint32_le(tx, int(address_restriction.mosaic_id[8:], 16))
    write_uint32_le(tx, int(address_restriction.mosaic_id[:8], 16))
    # Write restriction key
    write_uint32_le(tx, int(address_restriction.restriction_key[8:], 16))
    write_uint32_le(tx, int(address_restriction.restriction_key[:8], 16))
    # Write previous restriction value
    write_uint64_le(tx, int(address_restriction.previous_restriction_value))
    # Write new restriction value
    write_uint64_le(tx, int(address_restriction.new_restriction_value))
    # Write target address
    write_bytes(tx, base32.decode(address_restriction.target_address.address))

    return tx