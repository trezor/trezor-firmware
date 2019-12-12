from trezor import ui

from trezor.messages import ButtonRequestType
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction

from trezor.ui.text import Text
from trezor.utils import format_amount

from ..helpers import (
    NEM2_MAX_DIVISIBILITY,
    NEM2_MOSAIC_AMOUNT_DIVISOR,
)
from ..layout import require_confirm_final, require_confirm_text
from ..mosaic.helpers import get_mosaic_definition, is_nem_xem_mosaic

from apps.common.confirm import require_confirm
from apps.common.layout import split_address


async def ask_transfer(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    transfer: NEM2TransferTransaction,
    embedded=False
):
    for mosaic in transfer.mosaics:
        await ask_transfer_mosaic(ctx, common, transfer, mosaic)
    await _require_confirm_transfer(ctx, transfer.recipient_address.address, _get_xem_amount(transfer))

    if(transfer.message.payload):
        await _require_confirm_message(ctx, transfer.message.payload)
    if not embedded:
        await require_confirm_final(ctx, common.max_fee)


async def ask_transfer_mosaic(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    transfer: NEM2TransferTransaction,
    mosaic: NEMMosaic
):
    if is_nem_xem_mosaic(mosaic.id):
        return

    definition = get_mosaic_definition(mosaic.id, common.network_type)
    mosaic_amount = int(mosaic.amount) / NEM2_MOSAIC_AMOUNT_DIVISOR

    if definition:
        msg = Text("Confirm mosaic", ui.ICON_SEND, ui.GREEN)
        msg.normal("Confirm transfer of")
        msg.bold(
            format_amount(mosaic_amount, definition["divisibility"])
            + definition["ticker"]
        )
        msg.normal("of")
        msg.bold(definition["name"])
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)
    else:
        msg = Text("Confirm mosaic", ui.ICON_SEND, ui.RED)
        msg.bold("Unknown mosaic!")
        msg.normal("Divisibility")
        msg.normal("cannot be shown for")
        msg.normal("unknown mosaics")
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

        msg = Text("Confirm mosaic", ui.ICON_SEND, ui.GREEN)
        msg.normal("Confirm transfer of")
        msg.bold("%s raw units" % mosaic_amount)
        msg.normal("of")
        msg.bold("%s.%s" % (mosaic.id, mosaic.id))
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

def _get_xem_amount(transfer: NEM2TransferTransaction):
    for mosaic in transfer.mosaics:
        if is_nem_xem_mosaic(mosaic.id):
            return int(mosaic.amount) / NEM2_MOSAIC_AMOUNT_DIVISOR
    # if there are mosaics but do not include xem, 0 xem is sent
    return 0

async def ask_importance_transfer(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    imp: NEMImportanceTransfer
):
    if imp.mode == NEMImportanceTransferMode.ImportanceTransfer_Activate:
        m = "Activate"
    else:
        m = "Deactivate"
    await require_confirm_text(ctx, m + " remote harvesting?")
    if not embedded:
        await require_confirm_final(ctx, common.fee)


async def _require_confirm_transfer(ctx, recipient, value):
    text = Text("Confirm transfer", ui.ICON_SEND, ui.GREEN)
    text.bold("Send %s XEM" % format_amount(value, NEM2_MAX_DIVISIBILITY))
    text.normal("to")
    text.mono(*split_address(recipient))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)

async def _require_confirm_message(ctx, message):
    text = Text("Confirm message", ui.ICON_SEND, ui.GREEN)
    text.normal(message)
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
