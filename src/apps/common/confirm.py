from trezor import wire, ui, loop
from trezor.utils import unimport

# used to confirm/cancel the dialogs from outside of this module (i.e.
# through debug link)
signal = loop.Signal()


@unimport
async def confirm(session_id, content=None, code=None, *args, **kwargs):
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.wire_types import ButtonAck

    ui.display.clear()
    dialog = ConfirmDialog(content, *args, **kwargs)
    dialog.render()

    if code is None:
        code = Other
    await wire.reply_message(session_id, ButtonRequest(code=code), ButtonAck)
    return await loop.Wait((signal, dialog)) == CONFIRMED


@unimport
async def hold_to_confirm(session_id, content=None, code=None, *args, **kwargs):
    from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
    from trezor.ui.confirm import HoldToConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.wire_types import ButtonAck

    ui.display.clear()
    button = Button((0, 240 - 48, 240, 48), 'Hold to confirm',
                    normal_style=CONFIRM_BUTTON,
                    active_style=CONFIRM_BUTTON_ACTIVE)
    dialog = HoldToConfirmDialog(button, content, *args, **kwargs)

    if code is None:
        code = Other
    await wire.reply_message(session_id, ButtonRequest(code=code), ButtonAck)
    return await loop.Wait((signal, dialog)) == CONFIRMED


@unimport
async def require_confirm(*args, **kwargs):
    from trezor.messages.FailureType import ActionCancelled

    confirmed = await confirm(*args, **kwargs)

    if not confirmed:
        raise wire.FailureError(ActionCancelled, 'Cancelled')
