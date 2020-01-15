from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2MosaicGlobalRestrictionTransaction  import NEM2MosaicGlobalRestrictionTransaction
from trezor.messages.NEM2MosaicAddressRestrictionTransaction import NEM2MosaicAddressRestrictionTransaction

from . import layout, serialize

async def global_restriction(
    ctx,
    common: NEM2TransactionCommon,
    global_restriction: NEM2MosaicGlobalRestrictionTransaction
) -> bytearray:
    await layout.ask_global_restriction(ctx, common, global_restriction)
    return serialize.serialize_global_restriction(common, global_restriction)


async def address_restriction(
    ctx,
    common: NEM2TransactionCommon,
    address_restriction: NEM2MosaicAddressRestrictionTransaction
) -> bytearray:
    await layout.ask_address_restriction(ctx, common, address_restriction)
    return serialize.serialize_address_restriction(common, address_restriction)