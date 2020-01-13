from trezor import ui

from trezor.messages import ButtonRequestType
from trezor.messages.NEM2TransactionCommon import NEM2TransactionCommon
from trezor.messages.NEM2EmbeddedTransactionCommon import NEM2EmbeddedTransactionCommon
from trezor.messages.NEM2TransferTransaction import NEM2TransferTransaction

from trezor.ui.text import Text
from trezor.ui.scroll import Paginated
from trezor.utils import format_amount

from ..helpers import (
    NEM2_MAX_DIVISIBILITY,
    NEM2_MOSAIC_AMOUNT_DIVISOR,
    NEM2_MESSAGE_TYPE_ENCRYPTED
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
    properties = []

    text = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
    text.bold("Recipient:")
    text.br()
    text.mono(*split_address(transfer.recipient_address.address))
    properties.append(text)

    for mosaic in transfer.mosaics:
        mosaic_confirmation_sections = get_mosaic_confirmation_sections(ctx, common, transfer, mosaic)
        properties += mosaic_confirmation_sections

    if(transfer.message.payload):
        text = Text("Confirm properties", ui.ICON_SEND, new_lines=False)
        if(transfer.message.type == NEM2_MESSAGE_TYPE_ENCRYPTED):
            text.bold("Encrypted Message:")
            text.br()
            text.mono(*split_address(transfer.message.payload[:20] + "..." + transfer.message.payload[-20:]))
        else:
            text.bold("Plain Message:")
            text.br()
            text.normal(transfer.message.payload)
        properties.append(text)

    paginated = Paginated(properties)
    await require_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

    if not embedded:
        await require_confirm_final(ctx, common.max_fee)


def get_mosaic_confirmation_sections(
    ctx,
    common: NEM2TransactionCommon | NEM2EmbeddedTransactionCommon,
    transfer: NEM2TransferTransaction,
    mosaic: NEMMosaic
):

    mosaic_confirmation_sections = []

    definition = get_mosaic_definition(mosaic.id, common.network_type)
    mosaic_amount = int(mosaic.amount) / NEM2_MOSAIC_AMOUNT_DIVISOR

    if definition:
        msg = Text("Confirm mosaic", ui.ICON_SEND, ui.GREEN)
        msg.normal("Confirm transfer of")
        msg.bold(
            format_amount(mosaic_amount, definition["divisibility"])
            + definition["ticker"]
        )
        msg.normal("Namespace:")
        msg.bold(definition["namespace"])
        mosaic_confirmation_sections.append(msg)
    else:
        msg = Text("Confirm mosaic", ui.ICON_SEND, ui.GREEN)
        msg.normal("Confirm transfer of")
        msg.bold("%s raw units" % mosaic_amount)
        msg.normal("of")
        msg.bold("%s.%s" % (mosaic.id, mosaic.id))

def _get_xem_amount(transfer: NEM2TransferTransaction):
    for mosaic in transfer.mosaics:
        if is_nem_xem_mosaic(mosaic.id):
            return int(mosaic.amount) / NEM2_MOSAIC_AMOUNT_DIVISOR
    # if there are mosaics but do not include xem, 0 xem is sent
    return 0

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