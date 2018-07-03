from trezor.messages.NEMMosaicCreation import NEMMosaicCreation
from trezor.messages.NEMMosaicSupplyChange import NEMMosaicSupplyChange
from trezor.messages.NEMTransactionCommon import NEMTransactionCommon

from ..helpers import (
    NEM_TRANSACTION_TYPE_MOSAIC_CREATION,
    NEM_TRANSACTION_TYPE_MOSAIC_SUPPLY_CHANGE,
)
from ..writers import write_bytes_with_length, write_common, write_uint32, write_uint64


def serialize_mosaic_creation(
    common: NEMTransactionCommon, creation: NEMMosaicCreation, public_key: bytes
):
    w = write_common(
        common, bytearray(public_key), NEM_TRANSACTION_TYPE_MOSAIC_CREATION
    )

    mosaics_w = bytearray()
    write_bytes_with_length(mosaics_w, bytearray(public_key))
    identifier_length = (
        4 + len(creation.definition.namespace) + 4 + len(creation.definition.mosaic)
    )
    write_uint32(mosaics_w, identifier_length)
    write_bytes_with_length(mosaics_w, bytearray(creation.definition.namespace))
    write_bytes_with_length(mosaics_w, bytearray(creation.definition.mosaic))
    write_bytes_with_length(mosaics_w, bytearray(creation.definition.description))
    write_uint32(mosaics_w, 4)  # number of properties

    _write_property(mosaics_w, "divisibility", creation.definition.divisibility)
    _write_property(mosaics_w, "initialSupply", creation.definition.supply)
    _write_property(mosaics_w, "supplyMutable", creation.definition.mutable_supply)
    _write_property(mosaics_w, "transferable", creation.definition.transferable)

    if creation.definition.levy:
        levy_identifier_length = (
            4
            + len(creation.definition.levy_namespace)
            + 4
            + len(creation.definition.levy_mosaic)
        )
        write_uint32(
            mosaics_w,
            4
            + 4
            + len(creation.definition.levy_address)
            + 4
            + levy_identifier_length
            + 8,
        )
        write_uint32(mosaics_w, creation.definition.levy)
        write_bytes_with_length(mosaics_w, bytearray(creation.definition.levy_address))
        write_uint32(mosaics_w, levy_identifier_length)
        write_bytes_with_length(
            mosaics_w, bytearray(creation.definition.levy_namespace)
        )
        write_bytes_with_length(mosaics_w, bytearray(creation.definition.levy_mosaic))
        write_uint64(mosaics_w, creation.definition.fee)
    else:
        write_uint32(mosaics_w, 0)

    # write mosaic bytes with length
    write_bytes_with_length(w, mosaics_w)

    write_bytes_with_length(w, bytearray(creation.sink))
    write_uint64(w, creation.fee)

    return w


def serialize_mosaic_supply_change(
    common: NEMTransactionCommon, change: NEMMosaicSupplyChange, public_key: bytes
):
    w = write_common(
        common, bytearray(public_key), NEM_TRANSACTION_TYPE_MOSAIC_SUPPLY_CHANGE
    )

    identifier_length = 4 + len(change.namespace) + 4 + len(change.mosaic)
    write_uint32(w, identifier_length)
    write_bytes_with_length(w, bytearray(change.namespace))
    write_bytes_with_length(w, bytearray(change.mosaic))

    write_uint32(w, change.type)
    write_uint64(w, change.delta)
    return w


def _write_property(w: bytearray, name: str, value):
    if value is None:
        if name in ("divisibility", "initialSupply"):
            value = 0
        elif name in ("supplyMutable", "transferable"):
            value = False
    if type(value) == bool:
        if value:
            value = "true"
        else:
            value = "false"
    elif type(value) == int:
        value = str(value)
    elif type(value) != str:
        raise ValueError("Incompatible value type")
    write_uint32(w, 4 + len(name) + 4 + len(value))
    write_bytes_with_length(w, bytearray(name))
    write_bytes_with_length(w, bytearray(value))
