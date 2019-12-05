from trezor.crypto import random, base32
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2NamespaceRegistrationTransaction import NEM2NamespaceRegistrationTransaction
from ubinascii import hexlify, unhexlify

from ..helpers import (
    AES_BLOCK_SIZE,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
    NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
    NEM2_NAMESPACE_REGISTRATION_TYPE_SUB
)

from ..writers import serialize_tx_common, get_common_message_size

from apps.common.writers import (
    write_bytes,
    write_uint8,
    write_uint16_le,
    write_uint32_le,
    write_uint64_le
)
# reflect the serialization used here:
# https://github.com/nemtech/nem2-sdk-typescript-javascript/blob/master/src/infrastructure/catbuffer/TransferTransactionBodyBuilder.ts#L120
def serialize_namespace_registration(
    common: NEM2TransactionCommon,
    namespace_registration: NEM2NamespaceRegistrationTransaction
) -> bytearray:
    tx = bytearray()

    size = get_common_message_size()
    # add up the namespace_registration-specific message attribute sizes
    size += 8 # duration if root namespace or parent id if subnamespace
    size += 8 # namespace id
    size += 1 # registration type
    size += 1 # namespace name size
    size += len(namespace_registration.namespace_name) # namespace name

    write_uint32_le(tx, size)

    tx = serialize_tx_common(tx, common)

    # write_bytes(tx, "here".encode())

    # root namespace registration define their own duration
    if(namespace_registration.registration_type == NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT):
        write_uint64_le(tx, int(namespace_registration.duration))

    # child namespace registration reference a parent id
    if(namespace_registration.registration_type == NEM2_NAMESPACE_REGISTRATION_TYPE_SUB):
        write_uint64_le(tx, int(namespace_registration.parent_id, 16))

    write_uint64_le(tx, int(namespace_registration.id, 16))

    write_uint8(tx, namespace_registration.registration_type)

    write_uint8(tx, len(namespace_registration.namespace_name))

    write_bytes(tx, namespace_registration.namespace_name.encode())

    return tx