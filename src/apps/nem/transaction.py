
from .helpers import *
from .writers import *


def nem_transaction_create_transfer(network: int, timestamp: int, signer_public_key: bytes, fee: int, deadline: int,
                                    recipient: str, amount: int, payload: bytearray = None, encrypted: bool = False,
                                    mosaics: int = 0) -> bytearray:

    tx = _nem_transaction_write_common(NEM_TRANSACTION_TYPE_TRANSFER,
                                       _nem_get_version(network, mosaics),
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

    tx = _nem_transaction_write_common(NEM_TRANSACTION_TYPE_PROVISION_NAMESPACE,
                                       _nem_get_version(network),
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


def nem_transaction_create_mosaic_creation(network: int, timestamp: int, signer_public_key: bytes, fee:int,
                                           deadline: int, namespace: str, mosaic: str, description: str,
                                           divisibility: int, supply: int, mutable_supply: bool, transferable: bool,
                                           levy_type: int, levy_fee: int, levy_address: str, levy_namespace: str,
                                           levy_mosaic: str, creation_sink: str, creation_fee: int):

    w = _nem_transaction_write_common(NEM_TRANSACTION_TYPE_MOSAIC_CREATION,
                                       _nem_get_version(network),
                                       timestamp,
                                       signer_public_key,
                                       fee,
                                       deadline)

    mosaics_w = bytearray()
    write_bytes_with_length(mosaics_w, bytearray(signer_public_key))
    identifier_length = 4 + len(namespace) + 4 + len(mosaic)
    write_uint32(mosaics_w, identifier_length)
    write_bytes_with_length(mosaics_w, bytearray(namespace))
    write_bytes_with_length(mosaics_w, bytearray(mosaic))
    write_bytes_with_length(mosaics_w, bytearray(description))
    write_uint32(mosaics_w, 4)  # number of properties

    nem_write_mosaic(mosaics_w, "divisibility", divisibility)
    nem_write_mosaic(mosaics_w, "initialSupply", supply)
    nem_write_mosaic(mosaics_w, "supplyMutable", mutable_supply)
    nem_write_mosaic(mosaics_w, "transferable", transferable)

    if levy_type:
        levy_identifier_length = 4 + len(levy_namespace) + 4 + len(levy_mosaic)
        write_uint32(mosaics_w, 4 + 4 + len(levy_address) + 4 + levy_identifier_length + 8)
        write_uint32(mosaics_w, levy_type)
        write_bytes_with_length(mosaics_w, bytearray(levy_address))
        write_uint32(mosaics_w, levy_identifier_length)
        write_bytes_with_length(mosaics_w, bytearray(levy_namespace))
        write_bytes_with_length(mosaics_w, bytearray(levy_mosaic))
        write_uint64(mosaics_w, levy_fee)
    else:
        write_uint32(mosaics_w, 0)

    # write mosaic bytes with length
    write_bytes_with_length(w, mosaics_w)

    write_bytes_with_length(w, bytearray(creation_sink))
    write_uint64(w, creation_fee)

    return w


def nem_transaction_create_mosaic_supply_change(network: int, timestamp: int, signer_public_key: bytes,	fee: int,
                                                deadline: int, namespace: str, mosaic: str, type: int, delta: int):

    w = _nem_transaction_write_common(NEM_TRANSACTION_TYPE_MOSAIC_SUPPLY_CHANGE,
                                      _nem_get_version(network),
                                      timestamp,
                                      signer_public_key,
                                      fee,
                                      deadline)

    identifier_length = 4 + len(namespace) + 4 + len(mosaic)
    write_uint32(w, identifier_length)
    write_bytes_with_length(w, bytearray(namespace))
    write_bytes_with_length(w, bytearray(mosaic))

    write_uint32(w, type)
    write_uint64(w, delta)

    return w


def nem_transaction_create_importance_transfer(network: int, timestamp: int, signer_public_key: bytes, fee: int,
                                               deadline: int, mode: int, remote: bytes):

    w = _nem_transaction_write_common(NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER,
                                      _nem_get_version(network),
                                      timestamp,
                                      signer_public_key,
                                      fee,
                                      deadline)

    write_uint32(w, mode)
    write_bytes_with_length(w, bytearray(remote))


def nem_transaction_create_aggregate_modification(network: int, timestamp: int, signer_public_key: bytes, fee: int,
                                                  deadline: int, modifications: int, relative_change: bool):

    w = _nem_transaction_write_common(NEM_TRANSACTION_TYPE_AGGREGATE_MODIFICATION,
                                      _nem_get_version(network, relative_change),
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


def nem_write_mosaic(w: bytearray, name: str, value):
    if type(value) == bool:
        if value:
            value = "true"
        else:
            value = "false"
    elif type(value) == int:
        # todo might need more formatting
        value = str(value)
    elif type(value) != str:
        raise ValueError('Incompatible value type')
    write_uint32(w, 4 + len(name) + 4 + len(value))
    write_bytes_with_length(w, bytearray(name))
    write_bytes_with_length(w, bytearray(value))


def nem_transaction_write_mosaic(w: bytearray, namespace: str, mosaic: str, quantity: int):
    identifier_length = 4 + len(namespace) + 4 + len(mosaic)
    # indentifier length (u32) + quantity (u64) + identifier size
    write_uint32(w, 4 + 8 + identifier_length)
    write_uint32(w, identifier_length)
    write_bytes_with_length(w, bytearray(namespace))
    write_bytes_with_length(w, bytearray(mosaic))
    write_uint64(w, quantity)


def _nem_transaction_write_common(tx_type: int, version: int, timestamp: int, signer: bytes, fee: int, deadline: int)\
        -> bytearray:
    ret = bytearray()
    write_uint32(ret, tx_type)
    write_uint32(ret, version)
    write_uint32(ret, timestamp)

    write_bytes_with_length(ret, bytearray(signer))
    write_uint64(ret, fee)
    write_uint32(ret, deadline)

    return ret


def _nem_get_version(network, mosaics=None) -> int:
    if mosaics:
        return network << 24 | 2
    return network << 24 | 1
