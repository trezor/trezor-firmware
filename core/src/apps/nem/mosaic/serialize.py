from trezor.messages import (
    NEMMosaicCreation,
    NEMMosaicSupplyChange,
    NEMTransactionCommon,
)

from ..helpers import (
    NEM_TRANSACTION_TYPE_MOSAIC_CREATION,
    NEM_TRANSACTION_TYPE_MOSAIC_SUPPLY_CHANGE,
)
from ..writers import (
    serialize_tx_common,
    write_bytes_with_len,
    write_uint32_le,
    write_uint64_le,
)

if False:
    from trezor.utils import Writer


def serialize_mosaic_creation(
    common: NEMTransactionCommon, creation: NEMMosaicCreation, public_key: bytes
) -> bytes:
    w = serialize_tx_common(common, public_key, NEM_TRANSACTION_TYPE_MOSAIC_CREATION)

    mosaics_w = bytearray()
    write_bytes_with_len(mosaics_w, public_key)

    identifier_w = bytearray()
    write_bytes_with_len(identifier_w, creation.definition.namespace.encode())
    write_bytes_with_len(identifier_w, creation.definition.mosaic.encode())

    write_bytes_with_len(mosaics_w, identifier_w)
    write_bytes_with_len(mosaics_w, creation.definition.description.encode())
    write_uint32_le(mosaics_w, 4)  # number of properties

    _write_property(mosaics_w, "divisibility", creation.definition.divisibility)
    _write_property(mosaics_w, "initialSupply", creation.definition.supply)
    _write_property(mosaics_w, "supplyMutable", creation.definition.mutable_supply)
    _write_property(mosaics_w, "transferable", creation.definition.transferable)

    if creation.definition.levy:
        assert creation.definition.levy_namespace is not None
        assert creation.definition.levy_mosaic is not None
        assert creation.definition.levy_address is not None
        assert creation.definition.fee is not None

        levy_identifier_w = bytearray()
        write_bytes_with_len(
            levy_identifier_w, creation.definition.levy_namespace.encode()
        )
        write_bytes_with_len(
            levy_identifier_w, creation.definition.levy_mosaic.encode()
        )

        levy_w = bytearray()
        write_uint32_le(levy_w, creation.definition.levy)
        write_bytes_with_len(levy_w, creation.definition.levy_address.encode())
        write_bytes_with_len(levy_w, levy_identifier_w)
        write_uint64_le(levy_w, creation.definition.fee)

        write_bytes_with_len(mosaics_w, levy_w)
    else:
        write_uint32_le(mosaics_w, 0)  # no levy

    write_bytes_with_len(w, mosaics_w)

    write_bytes_with_len(w, creation.sink.encode())
    write_uint64_le(w, creation.fee)

    return w


def serialize_mosaic_supply_change(
    common: NEMTransactionCommon, change: NEMMosaicSupplyChange, public_key: bytes
) -> bytes:
    w = serialize_tx_common(
        common, public_key, NEM_TRANSACTION_TYPE_MOSAIC_SUPPLY_CHANGE
    )

    identifier_w = bytearray()
    write_bytes_with_len(identifier_w, change.namespace.encode())
    write_bytes_with_len(identifier_w, change.mosaic.encode())

    write_bytes_with_len(w, identifier_w)

    write_uint32_le(w, change.type)
    write_uint64_le(w, change.delta)
    return w


def _write_property(w: Writer, name: str, value: int | bool | str | None) -> None:
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
    if type(value) != str:
        raise ValueError("Incompatible value type")
    byte_name = name.encode()
    byte_value = value.encode()
    write_uint32_le(w, 4 + len(byte_name) + 4 + len(byte_value))
    write_bytes_with_len(w, byte_name)
    write_bytes_with_len(w, byte_value)
