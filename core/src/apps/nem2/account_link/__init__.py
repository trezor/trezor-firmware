from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2AccountLinkTransaction  import NEM2AccountLinkTransaction

from . import layout, serialize

async def account_link(
    ctx,
    common: NEM2TransactionCommon,
    account_link: NEM2AccountLinkTransaction
) -> bytearray:
    await layout.ask_account_link(ctx, common, account_link)
    return serialize.serialize_account_link(common, account_link)