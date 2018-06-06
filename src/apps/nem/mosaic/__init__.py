from trezor.messages.NEMTransactionCommon import NEMTransactionCommon
from trezor.messages.NEMMosaicCreation import NEMMosaicCreation
from trezor.messages.NEMMosaicSupplyChange import NEMMosaicSupplyChange

from . import layout, serialize


async def mosaic_creation(ctx, public_key: bytes, common: NEMTransactionCommon, creation: NEMMosaicCreation) -> bytearray:
    await layout.ask_mosaic_creation(ctx, common, creation)
    return serialize.serialize_mosaic_creation(common, creation, public_key)


async def supply_change(ctx, public_key: bytes, common: NEMTransactionCommon, change: NEMMosaicSupplyChange) -> bytearray:
    await layout.ask_supply_change(ctx, common, change)
    return serialize.serialize_mosaic_supply_change(common, change, public_key)
