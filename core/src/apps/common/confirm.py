from trezor import wire
from trezor.messages import ButtonRequestType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.confirm import CONFIRMED, Confirm, HoldToConfirm

if __debug__:
    from apps.debug import confirm_signal

if False:
    from typing import Any
    from trezor import ui
    from trezor.ui.confirm import ButtonContent, ButtonStyleType
    from trezor.ui.loader import LoaderStyleType


async def confirm(
    ctx: wire.Context,
    content: ui.Component,
    code: int = ButtonRequestType.Other,
    confirm: ButtonContent = Confirm.DEFAULT_CONFIRM,
    confirm_style: ButtonStyleType = Confirm.DEFAULT_CONFIRM_STYLE,
    cancel: ButtonContent = Confirm.DEFAULT_CANCEL,
    cancel_style: ButtonStyleType = Confirm.DEFAULT_CANCEL_STYLE,
    major_confirm: bool = False,
) -> bool:
    await ctx.call(ButtonRequest(code=code), ButtonAck)

    if content.__class__.__name__ == "Paginated":
        content.pages[-1] = Confirm(
            content.pages[-1],
            confirm,
            confirm_style,
            cancel,
            cancel_style,
            major_confirm,
        )
        dialog = content
    else:
        dialog = Confirm(
            content, confirm, confirm_style, cancel, cancel_style, major_confirm
        )

    if __debug__:
        return await ctx.wait(dialog, confirm_signal()) is CONFIRMED
    else:
        return await ctx.wait(dialog) is CONFIRMED


async def hold_to_confirm(
    ctx: wire.Context,
    content: ui.Component,
    code: int = ButtonRequestType.Other,
    confirm: ButtonContent = HoldToConfirm.DEFAULT_CONFIRM,
    confirm_style: ButtonStyleType = HoldToConfirm.DEFAULT_CONFIRM_STYLE,
    loader_style: LoaderStyleType = HoldToConfirm.DEFAULT_LOADER_STYLE,
) -> bool:
    await ctx.call(ButtonRequest(code=code), ButtonAck)

    if content.__class__.__name__ == "Paginated":
        content.pages[-1] = HoldToConfirm(
            content.pages[-1], confirm, confirm_style, loader_style
        )
        dialog = content
    else:
        dialog = HoldToConfirm(content, confirm, confirm_style, loader_style)

    if __debug__:
        return await ctx.wait(dialog, confirm_signal()) is CONFIRMED
    else:
        return await ctx.wait(dialog) is CONFIRMED


async def require_confirm(*args: Any, **kwargs: Any) -> None:
    confirmed = await confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled("Cancelled")


async def require_hold_to_confirm(*args: Any, **kwargs: Any) -> None:
    confirmed = await hold_to_confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled("Cancelled")
