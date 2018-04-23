from apps.nem.layout import *
from trezor.messages import NEMImportanceTransferMode
from trezor.messages import NEMTransfer
from trezor.messages import NEMImportanceTransfer
from trezor.messages import NEMTransactionCommon


async def ask_transfer(ctx, common: NEMTransactionCommon, transfer: NEMTransfer, payload, encrypted):
    if payload:
        await _require_confirm_payload(ctx, transfer.payload, encrypted)

    for mosaic in transfer.mosaics:
        await require_confirm_content(ctx, 'Confirm mosaic', _mosaics_message(mosaic))

    await _require_confirm_transfer(ctx, transfer.recipient, transfer.amount)

    await require_confirm_final(ctx, common.fee)


async def ask_importance_transfer(ctx, common: NEMTransactionCommon, imp: NEMImportanceTransfer):
    if imp.mode == NEMImportanceTransferMode.ImportanceTransfer_Activate:
        m = 'Activate'
    else:
        m = 'Deactivate'
    await require_confirm_text(ctx, m + ' remote harvesting?')
    await require_confirm_final(ctx, common.fee)


async def _require_confirm_transfer(ctx, recipient, value):
    content = Text('Confirm transfer', ui.ICON_SEND,
                   ui.BOLD, 'Send ' + format_amount(value, NEM_MAX_DIVISIBILITY) + ' XEM',
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(recipient),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def _require_confirm_payload(ctx, payload: bytes, encrypt=False):
    payload = str(payload, 'utf-8')

    if len(payload) > 48:
        payload = payload[:48] + '..'
    if encrypt:
        content = Text('Confirm payload', ui.ICON_SEND,
                       ui.BOLD, 'Encrypted:',
                       ui.NORMAL, *split_words(payload, 22),
                       icon_color=ui.GREEN)
    else:
        content = Text('Confirm payload', ui.ICON_SEND,
                       ui.BOLD, 'Unencrypted:',
                       ui.NORMAL, *split_words(payload, 22),
                       icon_color=ui.RED)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


def _mosaics_message(mosaic):
    return [ui.NORMAL, 'Confirm transfer of',
            ui.BOLD, str(mosaic.quantity) + ' raw units',
            ui.NORMAL, 'of',
            ui.BOLD, mosaic.namespace + '.' + mosaic.mosaic]
