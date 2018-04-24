from apps.nem.layout import *
from trezor.messages import NEMImportanceTransferMode
from trezor.messages import NEMTransfer
from trezor.messages import NEMImportanceTransfer
from trezor.messages import NEMTransactionCommon
from trezor.messages import NEMMosaic
from trezor.messages import NEMMosaicLevy
from apps.nem.mosaic.definitions import get_mosaic_definition


async def ask_transfer(ctx, common: NEMTransactionCommon, transfer: NEMTransfer, payload, encrypted):
    if payload:
        await _require_confirm_payload(ctx, transfer.payload, encrypted)

    for mosaic in transfer.mosaics:
        await ask_transfer_mosaic(ctx, mosaic, common.network)

    await _require_confirm_transfer(ctx, transfer.recipient, transfer.amount)

    await require_confirm_final(ctx, common.fee)


async def ask_transfer_mosaic(ctx, mosaic: NEMMosaic, network: int):
    definition = get_mosaic_definition(mosaic.namespace, mosaic.mosaic, network)

    if definition:
        msg = Text('Confirm mosaic', ui.ICON_SEND,
                   ui.NORMAL, 'Confirm transfer of',
                   ui.BOLD, format_amount(mosaic.quantity, definition["divisibility"]) + definition["ticker"],
                   ui.NORMAL, 'of',
                   ui.BOLD, definition["name"],
                   icon_color=ui.GREEN)
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

        if "levy" in definition and "fee" in definition:
            levy_msg = _get_levy_msg(definition, mosaic.quantity, network)
            msg = Text('Confirm mosaic', ui.ICON_SEND,
                       ui.NORMAL, 'Confirm mosaic',
                       ui.NORMAL, 'levy fee of',
                       ui.BOLD, levy_msg,
                       icon_color=ui.GREEN)
            await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

    else:
        msg = Text('Confirm mosaic', ui.ICON_SEND,
                   ui.BOLD, 'Unknown mosaic!',
                   ui.NORMAL, *split_words('Divisibility and levy cannot be shown for unknown mosaics', 22),
                   icon_color=ui.RED)
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

        msg = Text('Confirm mosaic', ui.ICON_SEND,
                   ui.NORMAL, 'Confirm transfer of',
                   ui.BOLD, str(mosaic.quantity) + ' raw units',
                   ui.NORMAL, 'of',
                   ui.BOLD, mosaic.namespace + '.' + mosaic.mosaic,
                   icon_color=ui.GREEN)
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)


def _get_levy_msg(mosaic_definition, quantity: int, network: int) -> str:
    levy_definition = get_mosaic_definition(mosaic_definition["levy_namespace"], mosaic_definition["levy_mosaic"], network)
    if mosaic_definition["levy"] == NEMMosaicLevy.MosaicLevy_Absolute:
        levy_fee = mosaic_definition["fee"]
    else:
        levy_fee = quantity * mosaic_definition["fee"] / NEM_LEVY_PERCENTILE_DIVISOR_ABSOLUTE
    return format_amount(levy_fee, levy_definition["divisibility"]) + levy_definition["ticker"]


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
