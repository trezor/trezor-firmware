
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


def _nem_get_version(network, mosaics) -> int:
    if mosaics:
        return network << 24 | 2
    return network << 24 | 1
