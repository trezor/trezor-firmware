from .writers import *
from trezor.messages.NEMMosaic import NEMMosaic
from trezor.messages import NEMSupplyChangeType
from apps.nem.layout import *


async def ask_mosaic_creation(ctx, msg: NEMSignTx):
    await require_confirm_action(ctx, 'Create mosaic "' + msg.mosaic_creation.definition.mosaic + '" under  namespace "'
                                 + msg.mosaic_creation.definition.namespace + '"?')
    await require_confirm_properties(ctx, msg.mosaic_creation.definition)
    await require_confirm_fee(ctx, 'Confirm creation fee', msg.mosaic_creation.fee)

    await require_confirm_final(ctx, msg.transaction.fee)


async def ask_mosaic_supply_change(ctx, msg: NEMSignTx):
    await require_confirm_action(ctx, 'Modify supply for "' + msg.supply_change.mosaic + '" under  namespace "'
                                 + msg.supply_change.namespace + '"?')
    if msg.supply_change.type == NEMSupplyChangeType.SupplyChange_Decrease:
        ask_msg = 'Decrease supply by ' + str(msg.supply_change.delta) + ' whole units?'
    elif msg.supply_change.type == NEMSupplyChangeType.SupplyChange_Increase:
        ask_msg = 'Increase supply by ' + str(msg.supply_change.delta) + ' whole units?'
    else:
        raise ValueError('Invalid supply change type')
    await require_confirm_action(ctx, ask_msg)

    await require_confirm_final(ctx, msg.transaction.fee)


def serialize_mosaic_creation(msg: NEMSignTx, public_key: bytes):
    w = write_common(msg.transaction, bytearray(public_key), NEM_TRANSACTION_TYPE_MOSAIC_CREATION)

    mosaics_w = bytearray()
    write_bytes_with_length(mosaics_w, bytearray(public_key))
    identifier_length = 4 + len(msg.mosaic_creation.definition.namespace) + 4 + len(msg.mosaic_creation.definition.mosaic)
    write_uint32(mosaics_w, identifier_length)
    write_bytes_with_length(mosaics_w, bytearray(msg.mosaic_creation.definition.namespace))
    write_bytes_with_length(mosaics_w, bytearray(msg.mosaic_creation.definition.mosaic))
    write_bytes_with_length(mosaics_w, bytearray(msg.mosaic_creation.definition.description))
    write_uint32(mosaics_w, 4)  # number of properties

    _write_property(mosaics_w, "divisibility", msg.mosaic_creation.definition.divisibility)
    _write_property(mosaics_w, "initialSupply", msg.mosaic_creation.definition.supply)
    _write_property(mosaics_w, "supplyMutable", msg.mosaic_creation.definition.mutable_supply)
    _write_property(mosaics_w, "transferable", msg.mosaic_creation.definition.transferable)

    if msg.mosaic_creation.definition.levy:
        levy_identifier_length = 4 + len(msg.mosaic_creation.definition.levy_namespace) + 4 + len(msg.mosaic_creation.definition.levy_mosaic)
        write_uint32(mosaics_w, 4 + 4 + len(msg.mosaic_creation.definition.levy_address) + 4 + levy_identifier_length + 8)
        write_uint32(mosaics_w, msg.mosaic_creation.definition.levy)
        write_bytes_with_length(mosaics_w, bytearray(msg.mosaic_creation.definition.levy_address))
        write_uint32(mosaics_w, levy_identifier_length)
        write_bytes_with_length(mosaics_w, bytearray(msg.mosaic_creation.definition.levy_namespace))
        write_bytes_with_length(mosaics_w, bytearray(msg.mosaic_creation.definition.levy_mosaic))
        write_uint64(mosaics_w, msg.mosaic_creation.definition.fee)
    else:
        write_uint32(mosaics_w, 0)

    # write mosaic bytes with length
    write_bytes_with_length(w, mosaics_w)

    write_bytes_with_length(w, bytearray(msg.mosaic_creation.sink))
    write_uint64(w, msg.mosaic_creation.fee)

    return w


def serialize_mosaic_supply_change(msg: NEMSignTx, public_key: bytes):
    w = write_common(msg.transaction, bytearray(public_key), NEM_TRANSACTION_TYPE_MOSAIC_SUPPLY_CHANGE)

    identifier_length = 4 + len(msg.supply_change.namespace) + 4 + len(msg.supply_change.mosaic)
    write_uint32(w, identifier_length)
    write_bytes_with_length(w, bytearray(msg.supply_change.namespace))
    write_bytes_with_length(w, bytearray(msg.supply_change.mosaic))

    write_uint32(w, msg.supply_change.type)
    write_uint64(w, msg.supply_change.delta)
    return w


def _write_property(w: bytearray, name: str, value):
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


def serialize_mosaic(w: bytearray, namespace: str, mosaic: str, quantity: int):
    identifier_length = 4 + len(namespace) + 4 + len(mosaic)
    # indentifier length (u32) + quantity (u64) + identifier size
    write_uint32(w, 4 + 8 + identifier_length)
    write_uint32(w, identifier_length)
    write_bytes_with_length(w, bytearray(namespace))
    write_bytes_with_length(w, bytearray(mosaic))
    write_uint64(w, quantity)


def canonicalize_mosaics(mosaics: list):
    if len(mosaics) <= 1:
        return mosaics
    mosaics = merge_mosaics(mosaics)
    return sort_mosaics(mosaics)


def are_mosaics_equal(a: NEMMosaic, b: NEMMosaic) -> bool:
    if a.namespace == b.namespace and a.mosaic == b.mosaic:
        return True
    return False


def merge_mosaics(mosaics: list) -> list:
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


def sort_mosaics(mosaics: list) -> list:
    return sorted(mosaics, key=lambda m: (m.namespace, m.mosaic))
