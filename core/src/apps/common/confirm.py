from trezor import wire
from trezor.messages import ButtonRequestType, MessageType
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.confirm import CONFIRMED, Confirm, HoldToConfirm

if __debug__:
    from apps.debug import confirm_signal


async def confirm(
    ctx,
    content,
    code=ButtonRequestType.Other,
    confirm=Confirm.DEFAULT_CONFIRM,
    confirm_style=Confirm.DEFAULT_CONFIRM_STYLE,
    cancel=Confirm.DEFAULT_CANCEL,
    cancel_style=Confirm.DEFAULT_CANCEL_STYLE,
):
    await ctx.call(ButtonRequest(code=code), MessageType.ButtonAck)

    if content.__class__.__name__ == "Paginated":
        content.pages[-1] = Confirm(
            content.pages[-1], confirm, confirm_style, cancel, cancel_style
        )
        dialog = content
    else:
        dialog = Confirm(content, confirm, confirm_style, cancel, cancel_style)

    if __debug__:
        return await ctx.wait(dialog, confirm_signal) is CONFIRMED
    else:
        return await ctx.wait(dialog) is CONFIRMED


async def hold_to_confirm(
    ctx,
    content,
    code=ButtonRequestType.Other,
    confirm=HoldToConfirm.DEFAULT_CONFIRM,
    confirm_style=HoldToConfirm.DEFAULT_CONFIRM_STYLE,
    loader_style=HoldToConfirm.DEFAULT_LOADER_STYLE,
):
    await ctx.call(ButtonRequest(code=code), MessageType.ButtonAck)

    if content.__class__.__name__ == "Paginated":
        content.pages[-1] = HoldToConfirm(
            content.pages[-1], confirm, confirm_style, loader_style
        )
        dialog = content
    else:
        dialog = HoldToConfirm(content, confirm, confirm_style, loader_style)

    if __debug__:
        return await ctx.wait(dialog, confirm_signal) is CONFIRMED
    else:
        return await ctx.wait(dialog) is CONFIRMED


async def require_confirm(*args, **kwargs):
    confirmed = await confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled("Cancelled")


async def require_hold_to_confirm(*args, **kwargs):
    confirmed = await hold_to_confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled("Cancelled")
