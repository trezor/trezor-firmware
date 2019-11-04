from trezor import ui
from trezor.messages import (
    ButtonRequestType,
    NEM2Mosaic,
    NEM2TransactionCommon,
    NEM2TransferTransaction,
)
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
    common: NEM2TransactionCommon,
    transfer: NEM2TransferTransaction
):
    for mosaic in transfer.mosaics:
        await ask_transfer_mosaic(ctx, common, transfer, mosaic)
    await _require_confirm_transfer(ctx, transfer.recipient_address, _get_xem_amount(transfer))
    await require_confirm_final(ctx, common.max_fee)


async def ask_transfer_mosaic(
    ctx, common: NEM2TransactionCommon, transfer: NEM2TransferTransaction, mosaic: NEMMosaic
):
    if is_nem_xem_mosaic(mosaic.id):
        return

    definition = get_mosaic_definition(mosaic.id, common.network_type)
    mosaic_quantity = mosaic.quantity * transfer.amount / NEM2_MOSAIC_AMOUNT_DIVISOR

    if definition:
        msg = Text("Confirm mosaic", ui.ICON_SEND, ui.GREEN)
        msg.normal("Confirm transfer of")
        msg.bold(
            format_amount(mosaic_quantity, definition["divisibility"])
            + definition["ticker"]
        )
        msg.normal("of")
        msg.bold(definition["name"])
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

        if "levy" in definition and "fee" in definition:
            levy_msg = _get_levy_msg(definition, mosaic_quantity, common.network)
            msg = Text("Confirm mosaic", ui.ICON_SEND, ui.GREEN)
            msg.normal("Confirm mosaic", "levy fee of")
            msg.bold(levy_msg)
            await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

    else:
        msg = Text("Confirm mosaic", ui.ICON_SEND, ui.RED)
        msg.bold("Unknown mosaic!")
        msg.normal("Divisibility and levy")
        msg.normal("cannot be shown for")
        msg.normal("unknown mosaics")
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)

        msg = Text("Confirm mosaic", ui.ICON_SEND, ui.GREEN)
        msg.normal("Confirm transfer of")
        msg.bold("%s raw units" % mosaic_quantity)
        msg.normal("of")
        msg.bold("%s.%s" % (mosaic.namespace, mosaic.mosaic))
        await require_confirm(ctx, msg, ButtonRequestType.ConfirmOutput)


def _get_xem_amount(transfer: NEM2TransferTransaction):
    for mosaic in transfer.mosaics:
        if is_nem_xem_mosaic(mosaic.id):
            return mosaic.amount / NEM2_MOSAIC_AMOUNT_DIVISOR
    # if there are mosaics but do not include xem, 0 xem is sent
    return 0


def _get_levy_msg(mosaic_definition, quantity: int, network: int) -> str:
    levy_definition = get_mosaic_definition(
        mosaic_definition["levy_namespace"], mosaic_definition["levy_mosaic"], network
    )
    if mosaic_definition["levy"] == NEMMosaicLevy.MosaicLevy_Absolute:
        levy_fee = mosaic_definition["fee"]
    else:
        levy_fee = (
            quantity * mosaic_definition["fee"] / NEM2_LEVY_PERCENTILE_DIVISOR_ABSOLUTE
        )
    return (
        format_amount(levy_fee, levy_definition["divisibility"])
        + levy_definition["ticker"]
    )


async def ask_importance_transfer(
    ctx, common: NEM2TransactionCommon, imp: NEMImportanceTransfer
):
    if imp.mode == NEMImportanceTransferMode.ImportanceTransfer_Activate:
        m = "Activate"
    else:
        m = "Deactivate"
    await require_confirm_text(ctx, m + " remote harvesting?")
    await require_confirm_final(ctx, common.fee)


async def _require_confirm_transfer(ctx, recipient, value):
    text = Text("Confirm transfer", ui.ICON_SEND, ui.GREEN)
    text.bold("Send %s XEM" % format_amount(value, NEM2_MAX_DIVISIBILITY))
    text.normal("to")
    text.mono(*split_address(recipient))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def _require_confirm_payload(ctx, payload: bytearray, encrypt=False):
    payload = bytes(payload).decode()

    if encrypt:
        text = Text("Confirm payload", ui.ICON_SEND, ui.GREEN)
        text.bold("Encrypted:")
        text.normal(*payload.split(" "))
    else:
        text = Text("Confirm payload", ui.ICON_SEND, ui.RED)
        text.bold("Unencrypted:")
        text.normal(*payload.split(" "))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)
