from trezor import wire
from trezor.messages import ButtonRequestType
from trezor.ui.components.tt.confirm import (
    CONFIRMED,
    INFO,
    Confirm,
    HoldToConfirm,
    InfoConfirm,
)

from . import button_request

if __debug__:
    from trezor.ui.components.tt.scroll import Paginated


if False:
    from typing import Any, Callable, Optional
    from trezor import ui
    from trezor.ui.components.tt.confirm import ButtonContent, ButtonStyleType
    from trezor.ui.loader import LoaderStyleType
    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType


async def confirm(
    ctx: wire.GenericContext,
    content: ui.Component,
    code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    confirm: Optional[ButtonContent] = Confirm.DEFAULT_CONFIRM,
    confirm_style: ButtonStyleType = Confirm.DEFAULT_CONFIRM_STYLE,
    cancel: Optional[ButtonContent] = Confirm.DEFAULT_CANCEL,
    cancel_style: ButtonStyleType = Confirm.DEFAULT_CANCEL_STYLE,
    major_confirm: bool = False,
) -> bool:
    await button_request(ctx, code=code)

    if content.__class__.__name__ == "Paginated":
        # The following works because asserts are omitted in non-debug builds.
        # IOW if the assert runs, that means __debug__ is True and Paginated is imported
        assert isinstance(content, Paginated)

        content.pages[-1] = Confirm(
            content.pages[-1],
            confirm,
            confirm_style,
            cancel,
            cancel_style,
            major_confirm,
        )
        dialog: ui.Layout = content
    else:
        dialog = Confirm(
            content, confirm, confirm_style, cancel, cancel_style, major_confirm
        )

    return await ctx.wait(dialog) is CONFIRMED


async def info_confirm(
    ctx: wire.GenericContext,
    content: ui.Component,
    info_func: Callable,
    code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    confirm: ButtonContent = InfoConfirm.DEFAULT_CONFIRM,
    confirm_style: ButtonStyleType = InfoConfirm.DEFAULT_CONFIRM_STYLE,
    cancel: ButtonContent = InfoConfirm.DEFAULT_CANCEL,
    cancel_style: ButtonStyleType = InfoConfirm.DEFAULT_CANCEL_STYLE,
    info: ButtonContent = InfoConfirm.DEFAULT_INFO,
    info_style: ButtonStyleType = InfoConfirm.DEFAULT_INFO_STYLE,
) -> bool:
    await button_request(ctx, code=code)

    dialog = InfoConfirm(
        content, confirm, confirm_style, cancel, cancel_style, info, info_style
    )

    while True:
        result = await ctx.wait(dialog)

        if result is INFO:
            await info_func(ctx)

        else:
            return result is CONFIRMED


async def hold_to_confirm(
    ctx: wire.GenericContext,
    content: ui.Component,
    code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    confirm: str = HoldToConfirm.DEFAULT_CONFIRM,
    confirm_style: ButtonStyleType = HoldToConfirm.DEFAULT_CONFIRM_STYLE,
    loader_style: LoaderStyleType = HoldToConfirm.DEFAULT_LOADER_STYLE,
    cancel: bool = True,
) -> bool:
    await button_request(ctx, code=code)

    if content.__class__.__name__ == "Paginated":
        # The following works because asserts are omitted in non-debug builds.
        # IOW if the assert runs, that means __debug__ is True and Paginated is imported
        assert isinstance(content, Paginated)

        content.pages[-1] = HoldToConfirm(
            content.pages[-1], confirm, confirm_style, loader_style, cancel
        )
        dialog: ui.Layout = content
    else:
        dialog = HoldToConfirm(content, confirm, confirm_style, loader_style, cancel)

    return await ctx.wait(dialog) is CONFIRMED


async def require_confirm(*args: Any, **kwargs: Any) -> None:
    confirmed = await confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled


async def require_hold_to_confirm(*args: Any, **kwargs: Any) -> None:
    confirmed = await hold_to_confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled
