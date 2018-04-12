from apps.nem.layout import *
from trezor.messages import NEMImportanceTransferMode
from trezor.messages import NEMSignTx


async def ask_transfer(ctx, msg: NEMSignTx, payload, encrypted):
    if payload:
        await require_confirm_payload(ctx, msg.transfer.payload, encrypted)

    for mosaic in msg.transfer.mosaics:
        await require_confirm_action(ctx, 'Confirm transfer of ' + str(mosaic.quantity) +
                                     ' raw units of ' + mosaic.namespace + '.' + mosaic.mosaic)

    await require_confirm_transfer(ctx, msg.transfer.recipient, msg.transfer.amount)

    await require_confirm_final(ctx, msg.transaction.fee)


async def ask_importance_transfer(ctx, msg: NEMSignTx):
    if msg.importance_transfer.mode == NEMImportanceTransferMode.ImportanceTransfer_Activate:
        m = 'Activate'
    else:
        m = 'Deactivate'
    await require_confirm_action(ctx, m + ' remote harvesting?')
    await require_confirm_final(ctx, msg.transaction.fee)
