from typing import TYPE_CHECKING

from . import layout, serialize

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import (
        NEMMosaicCreation,
        NEMMosaicSupplyChange,
        NEMTransactionCommon,
    )


async def mosaic_creation(
    public_key: AnyBytes,
    common: NEMTransactionCommon,
    creation: NEMMosaicCreation,
) -> bytearray:
    await layout.ask_mosaic_creation(common, creation)
    return serialize.serialize_mosaic_creation(common, creation, public_key)


async def supply_change(
    public_key: AnyBytes,
    common: NEMTransactionCommon,
    change: NEMMosaicSupplyChange,
) -> bytearray:
    await layout.ask_supply_change(common, change)
    return serialize.serialize_mosaic_supply_change(common, change, public_key)
