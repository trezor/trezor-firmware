from trezor import loop, ui, wire
from trezor.messages import ButtonRequestType, FailureType, wire_types
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.confirm import CONFIRMED, ConfirmDialog, HoldToConfirmDialog
from apps.common import cache

# used to confirm/cancel the dialogs from outside of this module (i.e.
# through debug link)
if __debug__:
    signal = cache.memory.setdefault('confirm_signal', loop.signal())


@ui.layout
async def confirm(ctx, content, code=None, *args, **kwargs):
    if code is None:
        code = ButtonRequestType.Other
    await ctx.call(ButtonRequest(code=code), wire_types.ButtonAck)

    dialog = ConfirmDialog(content, *args, **kwargs)

    if __debug__:
        waiter = ctx.wait(signal, dialog)
    else:
        waiter = ctx.wait(dialog)
    return await waiter == CONFIRMED


@ui.layout
async def hold_to_confirm(ctx, content, code=None, *args, **kwargs):
    if code is None:
        code = ButtonRequestType.Other
    await ctx.call(ButtonRequest(code=code), wire_types.ButtonAck)

    dialog = HoldToConfirmDialog(content, 'Hold to confirm', *args, **kwargs)

    if __debug__:
        waiter = ctx.wait(signal, dialog)
    else:
        waiter = ctx.wait(dialog)
    return await waiter == CONFIRMED


async def require_confirm(*args, **kwargs):
    confirmed = await confirm(*args, **kwargs)
    if not confirmed:
        raise wire.FailureError(FailureType.ActionCancelled, 'Cancelled')


async def require_hold_to_confirm(*args, **kwargs):
    confirmed = await hold_to_confirm(*args, **kwargs)
    if not confirmed:
        raise wire.FailureError(FailureType.ActionCancelled, 'Cancelled')
