from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2MosaicDefinitionTransaction import NEM2MosaicDefinitionTransaction

from . import layout, serialize

async def mosaic_definition(
    ctx, public_key: bytes, common: NEM2TransactionCommon, creation: NEM2MosaicDefinitionTransaction
) -> bytearray:
    await layout.ask_mosaic_definition(ctx, common, creation)
    return serialize.serialize_mosaic_definition(common, creation, public_key)