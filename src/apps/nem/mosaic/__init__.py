from .layout import *
from .serialize import *


async def mosaic_creation(ctx, public_key: bytes, common: NEMTransactionCommon, creation: NEMMosaicCreation) -> bytearray:
    await ask_mosaic_creation(ctx, common, creation)
    return serialize_mosaic_creation(common, creation, public_key)


async def supply_change(ctx, public_key: bytes, common: NEMTransactionCommon, change: NEMMosaicSupplyChange):
    await ask_supply_change(ctx, common, change)
    return serialize_mosaic_supply_change(common, change, public_key)
