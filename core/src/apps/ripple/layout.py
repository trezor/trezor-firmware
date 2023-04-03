from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_metadata, confirm_total

from .helpers import DECIMALS

if TYPE_CHECKING:
    from trezor.wire import Context


async def require_confirm_total(ctx: Context, total: int, fee: int) -> None:
    await confirm_total(
        ctx,
        format_amount(total, DECIMALS) + " XRP",
        format_amount(fee, DECIMALS) + " XRP",
    )


async def require_confirm_destination_tag(ctx: Context, tag: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_destination_tag",
        "Confirm tag",
        "Destination tag:\n{}",
        str(tag),
        ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_tx(ctx: Context, to: str, value: int) -> None:
    from trezor.ui.layouts import confirm_output

    await confirm_output(ctx, to, format_amount(value, DECIMALS) + " XRP")
