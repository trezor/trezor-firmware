
from .helpers import *
from .writers import *
from trezor.messages.NEMMosaic import NEMMosaic


def nem_transaction_create_mosaic_creation(network: int, timestamp: int, signer_public_key: bytes, fee:int,
                                           deadline: int, namespace: str, mosaic: str, description: str,
                                           divisibility: int, supply: int, mutable_supply: bool, transferable: bool,
                                           levy_type: int, levy_fee: int, levy_address: str, levy_namespace: str,
                                           levy_mosaic: str, creation_sink: str, creation_fee: int):

    w = nem_transaction_write_common(NEM_TRANSACTION_TYPE_MOSAIC_CREATION,
                                     nem_get_version(network),
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

    w = nem_transaction_write_common(NEM_TRANSACTION_TYPE_MOSAIC_SUPPLY_CHANGE,
                                     nem_get_version(network),
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


def nem_write_mosaic(w: bytearray, name: str, value):
    if value is None:
        if name in ['divisibility', 'initialSupply']:
            value = 0
        elif name in ['supplyMutable', 'transferable']:
            value = False
    if type(value) == bool:
        if value:
            value = "true"
        else:
            value = "false"
    elif type(value) == int:
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


def nem_canonicalize_mosaics(mosaics: list):
    if len(mosaics) <= 1:
        return mosaics
    mosaics = nem_merge_mosaics(mosaics)
    return nem_sort_mosaics(mosaics)


def are_mosaics_equal(a: NEMMosaic, b: NEMMosaic) -> bool:
    if a.namespace == b.namespace and a.mosaic == b.mosaic:
        return True
    return False


def nem_merge_mosaics(mosaics: list) -> list:
    if not len(mosaics):
        return list()
    ret = list()
    for i in mosaics:
        found = False
        for k, y in enumerate(ret):
            if are_mosaics_equal(i, y):
                ret[k].quantity += i.quantity
                found = True
        if not found:
            ret.append(i)
    return ret


def nem_sort_mosaics(mosaics: list) -> list:
    return sorted(mosaics, key=lambda m: (m.namespace, m.mosaic))
