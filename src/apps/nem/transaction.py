
from .helpers import *
from .writers import *


def nem_transaction_create_transfer(network: int, timestamp: int, signer_public_key: bytes, fee: int, deadline: int,
                                    recipient: str, amount: int, payload: bytearray = None, encrypted: bool = False,
                                    mosaics: int = 0) -> bytearray:

    tx = nem_transaction_write_common(NEM_TRANSACTION_TYPE_TRANSFER,
                                      nem_get_version(network, mosaics),
                                      timestamp,
                                      signer_public_key,
                                      fee,
                                      deadline)

    write_bytes_with_length(tx, bytearray(recipient))
    write_uint64(tx, amount)

    if payload:
        # payload + payload size (u32) + encryption flag (u32)
        write_uint32(tx, len(payload) + 2 * 4)
        if encrypted:
            write_uint32(tx, 0x02)
        else:
            write_uint32(tx, 0x01)
        write_bytes_with_length(tx, payload)
    else:
        write_uint32(tx, 0)

    if mosaics:
        write_uint32(tx, mosaics)

    return tx


def nem_transaction_create_provision_namespace(network: int, timestamp: int, signer_public_key: bytes, fee: int,
                                               deadline: int, namespace: str, parent: str, rental_sink: str,
                                               rental_fee: int) -> bytearray:

    tx = nem_transaction_write_common(NEM_TRANSACTION_TYPE_PROVISION_NAMESPACE,
                                      nem_get_version(network),
                                      timestamp,
                                      signer_public_key,
                                      fee,
                                      deadline)

    write_bytes_with_length(tx, bytearray(rental_sink))
    write_uint64(tx, rental_fee)
    write_bytes_with_length(tx, bytearray(namespace))
    if parent:
        write_bytes_with_length(tx, bytearray(parent))
    else:
        write_uint32(tx, 0xffffffff)

    return tx


def nem_transaction_create_importance_transfer(network: int, timestamp: int, signer_public_key: bytes, fee: int,
                                               deadline: int, mode: int, remote: bytes):

    w = nem_transaction_write_common(NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER,
                                     nem_get_version(network),
                                     timestamp,
                                     signer_public_key,
                                     fee,
                                     deadline)

    write_uint32(w, mode)
    write_bytes_with_length(w, bytearray(remote))
    return w


def nem_transaction_create_aggregate_modification(network: int, timestamp: int, signer_public_key: bytes, fee: int,
                                                  deadline: int, modifications: int, relative_change: bool):

    w = nem_transaction_write_common(NEM_TRANSACTION_TYPE_AGGREGATE_MODIFICATION,
                                     nem_get_version(network, relative_change),
                                     timestamp,
                                     signer_public_key,
                                     fee,
                                     deadline)
    write_uint32(w, modifications)
    return w


def nem_transaction_write_cosignatory_modification(w: bytearray, type: int, cosignatory: bytes):
    write_uint32(w, 4 + 4 + len(cosignatory))
    write_uint32(w, type)
    write_bytes_with_length(w, bytearray(cosignatory))
    return w


def nem_transaction_write_minimum_cosignatories(w: bytearray, relative_change: int):
    write_uint32(w, 4)
    write_uint32(w, relative_change)
