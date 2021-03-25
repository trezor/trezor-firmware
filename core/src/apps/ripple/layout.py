from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_metadata
from trezor.ui.layouts.tt.altcoin import confirm_total_ripple

from . import helpers


async def require_confirm_fee(ctx, fee):
    await confirm_metadata(
        ctx,
        "confirm_fee",
        title="Confirm fee",
        content="Transaction fee:\n{}",
        param=format_amount(fee, helpers.DECIMALS) + " XRP",
        hide_continue=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_destination_tag(ctx, tag):
    await confirm_metadata(
        ctx,
        "confirm_destination_tag",
        title="Confirm tag",
        content="Destination tag:\n{}",
        param=str(tag),
        hide_continue=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_tx(ctx, to, value):
    await confirm_total_ripple(ctx, to, format_amount(value, helpers.DECIMALS))
