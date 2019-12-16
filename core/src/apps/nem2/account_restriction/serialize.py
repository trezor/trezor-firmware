from trezor.crypto import base32

from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2AccountAddressRestrictionTransaction import NEM2AccountAddressRestrictionTransaction
from trezor.messages.NEM2AccountMosaicRestrictionTransaction import NEM2AccountMosaicRestrictionTransaction

from ubinascii import unhexlify, hexlify

from ..helpers import (
    NEM2_TRANSACTION_TYPE_ACCOUNT_ADDRESS_RESTRICTION,
    NEM2_TRANSACTION_TYPE_ACCOUNT_MOSAIC_RESTRICTION,
    NEM2_TRANSACTION_TYPE_ACCOUNT_OPERATION_RESTRICTION,
)

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

def serialize_account_restriction(
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    account_restriction: NEM2AccountAddressRestrictionTransaction | NEM2AccountMosaicRestrictionTransaction | NEM2AccountOperationRestrictionTransaction,
    embedded=False
) -> bytearray:
    tx = bytearray()
    entity_type = common.type

    # Total size is the size of the common transaction properties
    # + the secret lock transaction specific properties
    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += get_account_restriction_body_size(account_restriction, entity_type)

    # Write size
    write_uint32_le(tx, size)
    # Write the common properties
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)

    # Write the account restriction transaction body
    write_uint16_le(tx, account_restriction.restriction_type) # restriction type
    write_uint8(tx, len(account_restriction.restriction_additions)) # account restriction additions count
    write_uint8(tx, len(account_restriction.restriction_deletions)) # account restriction deletions count
    write_uint32_le(tx, 0) # padding

    # Combine addition and deletion arrays as their serialization is exactly
    # the same, with no padding needed between them.
    combined = account_restriction.restriction_additions + account_restriction.restriction_deletions
    for item in combined:
        if entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_ADDRESS_RESTRICTION:
            write_bytes(tx, base32.decode(item.address)) # Address
        elif entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_MOSAIC_RESTRICTION:
            write_uint64_le(tx, int(item, 16)) # Mosaic ID
        elif entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_OPERATION_RESTRICTION:
            write_uint16_le(tx, item) # Entity type

    return tx

def get_account_restriction_body_size(
    account_restriction: NEM2AccountAddressRestrictionTransaction | NEM2AccountMosaicRestrictionTransaction | NEM2AccountOperationRestrictionTransaction,
    entity_type: int
):
    # Add up the account address restriction specific message attribute sizes
    size = 2 # restriction flag is 2 bytes
    size += 1 # restriction additions count is 1 bytes
    size += 1 # restriction deletions count is 1 bytes
    size += 4 # reserved is 4 bytes

    # Combine addition and deletion arrays as their size calculation is exactly the same
    combined = account_restriction.restriction_additions + account_restriction.restriction_deletions
    for item in combined:
        if entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_ADDRESS_RESTRICTION:
            size += 25 # recipient is 25 bytes
        elif entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_MOSAIC_RESTRICTION:
            size += 8 # mosaic ID is 25 bytes
        elif entity_type == NEM2_TRANSACTION_TYPE_ACCOUNT_OPERATION_RESTRICTION:
            size += 2 # entity type is 2 bytes

    return size
