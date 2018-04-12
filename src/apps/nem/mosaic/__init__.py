from .layout import *
from .serialize import *


async def mosaic_creation(ctx, public_key: bytes, msg: NEMSignTx) -> bytearray:
    await ask_mosaic_creation(ctx, msg)
    return serialize_mosaic_creation(msg, public_key)


async def supply_change(ctx, public_key: bytes, msg: NEMSignTx):
    await ask_mosaic_supply_change(ctx, msg)
    return serialize_mosaic_supply_change(msg, public_key)
