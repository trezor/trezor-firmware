from trezor import wire, ui, loop
from apps.common import cache

# used to confirm/cancel the dialogs from outside of this module (i.e.
# through debug link)
if __debug__:
    signal = cache.memory.setdefault('confirm_signal', loop.signal())


@ui.layout
async def confirm(ctx, content, code=None, *args, **kwargs):
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.wire_types import ButtonAck

    ui.display.clear()
    dialog = ConfirmDialog(content, *args, **kwargs)
    dialog.render()

    if code is None:
        code = Other
    await ctx.call(ButtonRequest(code=code), ButtonAck)

    if __debug__:
        waiter = loop.wait(signal, dialog)
    else:
        waiter = dialog
    return await waiter == CONFIRMED


@ui.layout
async def hold_to_confirm(ctx, content, code=None, *args, **kwargs):
    from trezor.ui.confirm import HoldToConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.wire_types import ButtonAck

    ui.display.clear()

    dialog = HoldToConfirmDialog(content, 'Hold to confirm', *args, **kwargs)

    if code is None:
        code = Other
    await ctx.call(ButtonRequest(code=code), ButtonAck)

    if __debug__:
        waiter = loop.wait(signal, dialog)
    else:
        waiter = dialog
    return await waiter == CONFIRMED


async def require_confirm(*args, **kwargs):
    from trezor.messages.FailureType import ActionCancelled

    confirmed = await confirm(*args, **kwargs)

    if not confirmed:
        raise wire.FailureError(ActionCancelled, 'Cancelled')
