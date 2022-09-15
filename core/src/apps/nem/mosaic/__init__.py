from typing import TYPE_CHECKING

from . import layout, serialize

if TYPE_CHECKING:
    from trezor.messages import (
        NEMMosaicCreation,
        NEMMosaicSupplyChange,
        NEMTransactionCommon,
    )
    from trezor.wire import Context


async def mosaic_creation(
    ctx: Context,
    public_key: bytes,
    common: NEMTransactionCommon,
    creation: NEMMosaicCreation,
) -> bytes:
    await layout.ask_mosaic_creation(ctx, common, creation)
    return serialize.serialize_mosaic_creation(common, creation, public_key)


async def supply_change(
    ctx: Context,
    public_key: bytes,
    common: NEMTransactionCommon,
    change: NEMMosaicSupplyChange,
) -> bytes:
    await layout.ask_supply_change(ctx, common, change)
    return serialize.serialize_mosaic_supply_change(common, change, public_key)
