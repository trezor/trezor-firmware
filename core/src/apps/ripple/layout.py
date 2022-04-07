from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_metadata
from trezor.ui.layouts.altcoin import confirm_total_ripple

from . import helpers

if TYPE_CHECKING:
    from trezor.wire import Context


async def require_confirm_fee(ctx: Context, fee: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_fee",
        title="Confirm fee",
        content="Transaction fee:\n{}",
        param=format_amount(fee, helpers.DECIMALS) + " XRP",
        hide_continue=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_destination_tag(ctx: Context, tag: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_destination_tag",
        title="Confirm tag",
        content="Destination tag:\n{}",
        param=str(tag),
        hide_continue=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_tx(ctx: Context, to: str, value: int) -> None:
    await confirm_total_ripple(ctx, to, format_amount(value, helpers.DECIMALS))
