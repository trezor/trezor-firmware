from trezor import ui
from trezor.messages import (ButtonRequestType, NEMImportanceTransfer,
                             NEMImportanceTransferMode, NEMMosaic,
                             NEMMosaicLevy, NEMTransactionCommon, NEMTransfer)
from trezor.ui.text import Text
from trezor.utils import format_amount, split_words

from apps.common.confirm import require_confirm

from ..helpers import (NEM_LEVY_PERCENTILE_DIVISOR_ABSOLUTE,
                       NEM_MAX_DIVISIBILITY, NEM_MOSAIC_AMOUNT_DIVISOR)
from ..layout import require_confirm_final, require_confirm_text, split_address
from ..mosaic.helpers import get_mosaic_definition, is_nem_xem_mosaic


async def ask_transfer(ctx, common: NEMTransactionCommon, transfer: NEMTransfer, payload: bytes, encrypted: bool):
    if payload:
        await _require_confirm_payload(ctx, transfer.payload, encrypted)
    for mosaic in transfer.mosaics:
        await ask_transfer_mosaic(ctx, common, transfer, mosaic)
    await _require_confirm_transfer(ctx, transfer.recipient, _get_xem_amount(transfer))
    await require_confirm_final(ctx, common.fee)


async def ask_transfer_mosaic(ctx, common: NEMTransactionCommon, transfer: NEMTransfer, mosaic: NEMMosaic):
    if is_nem_xem_mosaic(mosaic.namespace, mosaic.mosaic):
        return

    definition = get_mosaic_definition(mosaic.namespace, mosaic.mosaic, common.network)
    mosaic_quantity = mosaic.quantity * transfer.amount / NEM_MOSAIC_AMOUNT_DIVISOR

    if definition:
        msg = Text('Confirm mosaic', ui.ICON_SEND,
                   'Confirm transfer of',
                   ui.BOLD, format_amount(mosaic_quantity, definition['divisibility']) + definition['ticker'],
                   ui.NORMAL, 'of',
                   ui.BOLD, definition['name'],
                   icon_color=ui.GREEN)

        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

        if 'levy' in definition and 'fee' in definition:
            levy_msg = _get_levy_msg(definition, mosaic_quantity, common.network)
            msg = Text('Confirm mosaic', ui.ICON_SEND,
                       'Confirm mosaic',
                       'levy fee of',
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
                   ui.BOLD, '%s raw units' % mosaic_quantity,
                   ui.NORMAL, 'of',
                   ui.BOLD, '%s.%s' % (mosaic.namespace, mosaic.mosaic),
                   icon_color=ui.GREEN)
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)


def _get_xem_amount(transfer: NEMTransfer):
    # if mosaics are empty the transfer.amount denotes the xem amount
    if not transfer.mosaics:
        return transfer.amount
    # otherwise xem amount is taken from the nem xem mosaic if present
    for mosaic in transfer.mosaics:
        if is_nem_xem_mosaic(mosaic.namespace, mosaic.mosaic):
            return mosaic.quantity * transfer.amount / NEM_MOSAIC_AMOUNT_DIVISOR
    # if there are mosaics but do not include xem, 0 xem is sent
    return 0


def _get_levy_msg(mosaic_definition, quantity: int, network: int) -> str:
    levy_definition = get_mosaic_definition(
        mosaic_definition['levy_namespace'],
        mosaic_definition['levy_mosaic'],
        network)
    if mosaic_definition['levy'] == NEMMosaicLevy.MosaicLevy_Absolute:
        levy_fee = mosaic_definition['fee']
    else:
        levy_fee = quantity * mosaic_definition['fee'] / NEM_LEVY_PERCENTILE_DIVISOR_ABSOLUTE
    return format_amount(
        levy_fee,
        levy_definition['divisibility']
    ) + levy_definition['ticker']


async def ask_importance_transfer(ctx, common: NEMTransactionCommon, imp: NEMImportanceTransfer):
    if imp.mode == NEMImportanceTransferMode.ImportanceTransfer_Activate:
        m = 'Activate'
    else:
        m = 'Deactivate'
    await require_confirm_text(ctx, m + ' remote harvesting?')
    await require_confirm_final(ctx, common.fee)


async def _require_confirm_transfer(ctx, recipient, value):
    content = Text('Confirm transfer', ui.ICON_SEND,
                   ui.BOLD, 'Send %s XEM' % format_amount(value, NEM_MAX_DIVISIBILITY),
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
