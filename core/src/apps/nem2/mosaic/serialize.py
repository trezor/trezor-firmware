from trezor.messages.NEM2MosaicDefinitionTransaction import NEM2MosaicDefinitionTransaction
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon

from ..helpers import (
    NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
)
from ..writers import (
    serialize_tx_common,
    write_bytes_with_len,
    write_uint32_le,
    write_uint64_le,
)


def serialize_mosaic_definition(
    common: NEM2TransactionCommon, creation: NEM2MosaicDefinitionTransaction, public_key: bytes
):
    tx = serialize_tx_common(
        common,
        public_key,
        NEM2_TRANSACTION_TYPE_MOSAIC_DEFINITION,
        _get_version(common.network_type),
    )

    # mosaics_w = bytearray()
    # write_bytes_with_len(mosaics_w, public_key)

    # identifier_w = bytearray()
    # write_bytes_with_len(identifier_w, creation.definition.namespace.encode())
    # write_bytes_with_len(identifier_w, creation.definition.mosaic.encode())

    # write_bytes_with_len(mosaics_w, identifier_w)
    # write_bytes_with_len(mosaics_w, creation.definition.description.encode())
    # write_uint32_le(mosaics_w, 4)  # number of properties

    # _write_property(mosaics_w, "divisibility", creation.definition.divisibility)
    # _write_property(mosaics_w, "initialSupply", creation.definition.supply)
    # _write_property(mosaics_w, "supplyMutable", creation.definition.mutable_supply)
    # _write_property(mosaics_w, "transferable", creation.definition.transferable)

    # if creation.definition.levy:

    #     levy_identifier_w = bytearray()
    #     write_bytes_with_len(
    #         levy_identifier_w, creation.definition.levy_namespace.encode()
    #     )
    #     write_bytes_with_len(
    #         levy_identifier_w, creation.definition.levy_mosaic.encode()
    #     )

    #     levy_w = bytearray()
    #     write_uint32_le(levy_w, creation.definition.levy)
    #     write_bytes_with_len(levy_w, creation.definition.levy_address.encode())
    #     write_bytes_with_len(levy_w, levy_identifier_w)
    #     write_uint64_le(levy_w, creation.definition.fee)

    #     write_bytes_with_len(mosaics_w, levy_w)
    # else:
    #     write_uint32_le(mosaics_w, 0)  # no levy

    # write_bytes_with_len(w, mosaics_w)

    # write_bytes_with_len(w, creation.sink.encode())
    # write_uint64_le(w, creation.fee)

    return tx


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
    if type(value) != str:
        raise ValueError("Incompatible value type")
    name = name.encode()
    value = value.encode()
    write_uint32_le(w, 4 + len(name) + 4 + len(value))
    write_bytes_with_len(w, name)
    write_bytes_with_len(w, value)

def _get_version(network, mosaics=None) -> int:
    if mosaics:
        return network << 24 | 2
    return network << 24 | 1