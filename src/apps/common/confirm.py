from trezor import ui, wire
from trezor.messages import ButtonRequestType, MessageType
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.confirm import CONFIRMED, ConfirmDialog, HoldToConfirmDialog


@ui.layout
async def confirm(ctx, content, code=None, *args, **kwargs):
    if code is None:
        code = ButtonRequestType.Other
    await ctx.call(ButtonRequest(code=code), MessageType.ButtonAck)

    dialog = ConfirmDialog(content, *args, **kwargs)

    return await ctx.wait(dialog) == CONFIRMED


@ui.layout
async def hold_to_confirm(ctx, content, code=None, *args, **kwargs):
    if code is None:
        code = ButtonRequestType.Other
    await ctx.call(ButtonRequest(code=code), MessageType.ButtonAck)

    dialog = HoldToConfirmDialog(content, 'Hold to confirm', *args, **kwargs)

    return await ctx.wait(dialog) == CONFIRMED


async def require_confirm(*args, **kwargs):
    confirmed = await confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled('Cancelled')


async def require_hold_to_confirm(*args, **kwargs):
    confirmed = await hold_to_confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled('Cancelled')
