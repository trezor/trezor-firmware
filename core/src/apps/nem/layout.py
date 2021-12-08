from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_metadata, confirm_properties

from .helpers import NEM_MAX_DIVISIBILITY

if TYPE_CHECKING:
    from trezor.wire import Context


async def require_confirm_text(ctx: Context, action: str) -> None:
    await confirm_metadata(
        ctx,
        "confirm_nem",
        title="Confirm action",
        content=action,
        hide_continue=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_fee(ctx: Context, action: str, fee: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_fee",
        title="Confirm fee",
        content=action + "\n{}",
        param=f"{format_amount(fee, NEM_MAX_DIVISIBILITY)} XEM",
        hide_continue=True,
        br_code=ButtonRequestType.ConfirmOutput,
    )


async def require_confirm_content(ctx: Context, headline: str, content: list) -> None:
    await confirm_properties(
        ctx,
        "confirm_content",
        title=headline,
        props=content,
    )


async def require_confirm_final(ctx: Context, fee: int) -> None:
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await confirm_metadata(
        ctx,
        "confirm_final",
        title="Final confirm",
        content="Sign this transaction\n{}\nfor network fee?",
        param=f"and pay {format_amount(fee, NEM_MAX_DIVISIBILITY)} XEM",
        hide_continue=True,
        hold=True,
    )
