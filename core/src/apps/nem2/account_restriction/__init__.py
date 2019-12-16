from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2AccountAddressRestrictionTransaction import NEM2AccountAddressRestrictionTransaction
from trezor.messages.NEM2AccountMosaicRestrictionTransaction import NEM2AccountMosaicRestrictionTransaction
from trezor.messages.NEM2AccountOperationRestrictionTransaction import NEM2AccountOperationRestrictionTransaction

from . import layout, serialize

async def account_restriction(
    ctx,
    common: NEM2TransactionCommon,
    account_restriction: NEM2AccountAddressRestrictionTransaction | NEM2AccountMosaicRestrictionTransaction | NEM2AccountOperationRestrictionTransaction
) -> bytearray:
    await layout.ask_account_restriction(ctx, common, account_restriction)
    return serialize.serialize_account_restriction(common, account_restriction)
