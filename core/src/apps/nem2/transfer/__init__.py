from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction

from . import layout, serialize

async def transfer(
    ctx, common: NEM2TransactionCommon, transfer: NEM2TransferTransaction
):
    await layout.ask_transfer(ctx, common, transfer)
    return serialize.serialize_transfer(common, transfer)
