from typing import TYPE_CHECKING

from trezor import ui
from trezor.enums import ButtonRequestType, NEMImportanceTransferMode, NEMMosaicLevy
from trezor.messages import (
    NEMImportanceTransfer,
    NEMMosaic,
    NEMTransactionCommon,
    NEMTransfer,
)
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_action,
    confirm_output,
    confirm_properties,
    confirm_text,
)

from ..helpers import (
    NEM_LEVY_PERCENTILE_DIVISOR_ABSOLUTE,
    NEM_MAX_DIVISIBILITY,
    NEM_MOSAIC_AMOUNT_DIVISOR,
)
from ..layout import require_confirm_final, require_confirm_text
from ..mosaic.helpers import get_mosaic_definition, is_nem_xem_mosaic

if TYPE_CHECKING:
    from trezor.wire import Context
    from ..mosaic.nem_mosaics import MosaicLevy


async def ask_transfer(
    ctx: Context,
    common: NEMTransactionCommon,
    transfer: NEMTransfer,
    encrypted: bool,
) -> None:
    if transfer.payload:
        await _require_confirm_payload(ctx, transfer.payload, encrypted)
    for mosaic in transfer.mosaics:
        await ask_transfer_mosaic(ctx, common, transfer, mosaic)
    await _require_confirm_transfer(ctx, transfer.recipient, _get_xem_amount(transfer))
    await require_confirm_final(ctx, common.fee)


async def ask_transfer_mosaic(
    ctx: Context, common: NEMTransactionCommon, transfer: NEMTransfer, mosaic: NEMMosaic
) -> None:
    if is_nem_xem_mosaic(mosaic):
        return

    definition = get_mosaic_definition(mosaic.namespace, mosaic.mosaic, common.network)
    mosaic_quantity = mosaic.quantity * transfer.amount // NEM_MOSAIC_AMOUNT_DIVISOR

    if definition:
        await confirm_properties(
            ctx,
            "confirm_mosaic",
            title="Confirm mosaic",
            props=[
                (
                    "Confirm transfer of",
                    format_amount(mosaic_quantity, definition.divisibility)
                    + definition.ticker,
                ),
                ("of", definition.name),
            ],
        )

        if definition.levy is not None:
            levy_fee = _get_levy_fee(definition.levy, mosaic_quantity)
            levy_msg = (
                format_amount(levy_fee, definition.divisibility) + definition.ticker
            )

            await confirm_properties(
                ctx,
                "confirm_mosaic_levy",
                title="Confirm mosaic",
                props=[
                    ("Confirm mosaic\nlevy fee of", levy_msg),
                ],
            )

    else:
        await confirm_action(
            ctx,
            "confirm_mosaic_unknown",
            title="Confirm mosaic",
            action="Unknown mosaic!",
            description="Divisibility and levy cannot be shown for unknown mosaics",
            icon=ui.ICON_SEND,
            icon_color=ui.RED,
            br_code=ButtonRequestType.ConfirmOutput,
        )

        await confirm_properties(
            ctx,
            "confirm_mosaic_transfer",
            title="Confirm mosaic",
            props=[
                ("Confirm transfer of", f"{mosaic_quantity} raw units"),
                ("of", f"{mosaic.namespace}.{mosaic.mosaic}"),
            ],
        )


def _get_xem_amount(transfer: NEMTransfer) -> int:
    # if mosaics are empty the transfer.amount denotes the xem amount
    if not transfer.mosaics:
        return transfer.amount
    # otherwise xem amount is taken from the nem xem mosaic if present
    for mosaic in transfer.mosaics:
        if is_nem_xem_mosaic(mosaic):
            return mosaic.quantity * transfer.amount // NEM_MOSAIC_AMOUNT_DIVISOR
    # if there are mosaics but do not include xem, 0 xem is sent
    return 0


def _get_levy_fee(levy: MosaicLevy, quantity: int) -> int:
    if levy.type == NEMMosaicLevy.MosaicLevy_Absolute:
        return levy.fee
    else:
        return quantity * levy.fee // NEM_LEVY_PERCENTILE_DIVISOR_ABSOLUTE


async def ask_importance_transfer(
    ctx: Context, common: NEMTransactionCommon, imp: NEMImportanceTransfer
) -> None:
    if imp.mode == NEMImportanceTransferMode.ImportanceTransfer_Activate:
        m = "Activate"
    else:
        m = "Deactivate"
    await require_confirm_text(ctx, m + " remote harvesting?")
    await require_confirm_final(ctx, common.fee)


async def _require_confirm_transfer(ctx: Context, recipient: str, value: int) -> None:
    await confirm_output(
        ctx,
        recipient,
        amount=f"Send {format_amount(value, NEM_MAX_DIVISIBILITY)} XEM",
        font_amount=ui.BOLD,
        title="Confirm transfer",
        to_str="\nto\n",
    )


async def _require_confirm_payload(
    ctx: Context, payload: bytes, encrypted: bool = False
) -> None:
    await confirm_text(
        ctx,
        "confirm_payload",
        title="Confirm payload",
        description="Encrypted:" if encrypted else "Unencrypted:",
        data=bytes(payload).decode(),
        icon_color=ui.GREEN if encrypted else ui.RED,
        br_code=ButtonRequestType.ConfirmOutput,
    )
