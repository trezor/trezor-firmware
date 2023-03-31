from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_metadata

from .helpers import NEM_MAX_DIVISIBILITY

if TYPE_CHECKING:
    from trezor.wire import Context


async def require_confirm_text(ctx: Context, action: str) -> None:
    await confirm_metadata(
        ctx,
        "confirm_nem",
        "Confirm action",
        action,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_fee(ctx: Context, action: str, fee: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_fee",
        "Confirm fee",
        action + "\n{}",
        f"{format_amount(fee, NEM_MAX_DIVISIBILITY)} XEM",
        ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_content(ctx: Context, headline: str, content: list) -> None:
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        ctx,
        "confirm_content",
        headline,
        content,
    )


async def require_confirm_final(ctx: Context, fee: int) -> None:
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await confirm_metadata(
        ctx,
        "confirm_final",
        "Final confirm",
        "Sign this transaction\n{}\nfor network fee?",
        f"and pay {format_amount(fee, NEM_MAX_DIVISIBILITY)} XEM",
        hold=True,
    )
