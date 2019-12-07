from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2MosaicDefinitionTransaction import NEM2MosaicDefinitionTransaction
from trezor.messages.NEM2MosaicSupplyChangeTransaction import NEM2MosaicSupplyChangeTransaction

from . import layout, serialize

async def mosaic_definition(
    ctx, public_key: bytes, common: NEM2TransactionCommon, creation: NEM2MosaicDefinitionTransaction
) -> bytearray:
    await layout.ask_mosaic_definition(ctx, common, creation)
    return serialize.serialize_mosaic_definition(common, creation)

async def mosaic_supply(
    ctx, common: NEM2TransactionCommon, supply: NEM2MosaicSupplyChangeTransaction
) -> bytearray:
    # TODO: await layout.ask_mosaic_supply(ctx, common, supply)
    return serialize.serialize_mosaic_supply(common, supply)