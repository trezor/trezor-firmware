from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_metadata

from .helpers import DECIMALS

if TYPE_CHECKING:
    from trezor.wire import Context


async def require_confirm_fee(ctx: Context, fee: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_fee",
        "Confirm fee",
        "Transaction fee:\n{}",
        format_amount(fee, DECIMALS) + " XRP",
        ButtonRequestType.ConfirmOutput,
        hide_continue=True,
    )


async def require_confirm_destination_tag(ctx: Context, tag: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_destination_tag",
        "Confirm tag",
        "Destination tag:\n{}",
        str(tag),
        ButtonRequestType.ConfirmOutput,
        hide_continue=True,
    )


async def require_confirm_tx(ctx: Context, to: str, value: int) -> None:
    # NOTE: local imports here saves 4 bytes
    from trezor.ui.layouts.altcoin import confirm_total_ripple

    await confirm_total_ripple(ctx, to, format_amount(value, DECIMALS))
