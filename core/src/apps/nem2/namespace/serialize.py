from trezor.crypto import random, base32
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2NamespaceRegistrationTransaction import NEM2NamespaceRegistrationTransaction
from trezor.messages.NEM2AddressAliasTransaction import NEM2AddressAliasTransaction
from ubinascii import hexlify, unhexlify

from ..helpers import (
    AES_BLOCK_SIZE,
    NEM2_TRANSACTION_TYPE_NAMESPACE_REGISTRATION,
    NEM2_NAMESPACE_REGISTRATION_TYPE_ROOT,
    NEM2_NAMESPACE_REGISTRATION_TYPE_SUB
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

def serialize_namespace_registration(
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    namespace_registration: NEM2NamespaceRegistrationTransaction,
    embedded = False
) -> bytearray:
    tx = bytearray()

    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += get_namespace_registration_body_size(namespace_registration)

    write_uint32_le(tx, size)
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)
    write_bytes(tx, serialize_namespace_registration_body(namespace_registration))

    return tx

def serialize_namespace_registration_body(
    namespace_registration: NEM2NamespaceRegistrationTransaction
) -> bytearray:
    tx = bytearray()

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


def get_namespace_registration_body_size(namespace_registration: NEM2NamespaceRegistrationTransaction):
    # add up the namespace registration message attribute sizes
    size = 8 # duration if root namespace or parent id if subnamespace
    size += 8 # namespace id
    size += 1 # registration type
    size += 1 # namespace name size
    size += len(namespace_registration.namespace_name) # namespace name

    return size

def serialize_address_alias(
    common: NEM2TransactionCommon,
    address_alias: NEM2AddressAliasTransaction,
    embedded = False
) -> bytearray:
    tx = bytearray()

    size = get_common_message_size() if not embedded else get_embedded_common_message_size()
    size += get_address_alias_body_size()

    write_uint32_le(tx, size)
    serialize_tx_common(tx, common) if not embedded else serialize_embedded_tx_common(tx, common)
    write_bytes(tx, serialize_address_alias_body(address_alias))

    return tx

def get_address_alias_body_size():
    # add up the address alias message attribute sizes
    size = 8 # namespace id
    size += 25 # address (catbuffer UnresolvedAddress)
    size += 1 # alias action

    return size

def serialize_address_alias_body(address_alias: NEM2AddressAliasTransaction) -> bytearray:

    tx = bytearray()

    write_uint64_le(tx, int(address_alias.namespace_id, 16))

    # address (catbuffer UnresolvedAddress - 25 bits) base 32 encoded
    write_bytes(tx, base32.decode(address_alias.address.address))

    write_uint8(tx, address_alias.alias_action)

    return tx