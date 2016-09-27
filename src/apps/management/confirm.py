from trezor import wire
from trezor.utils import unimport


@unimport
async def confirm(session_id, content=None, code=None, **kwargs):
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.wire_types import ButtonAck

    dialog = ConfirmDialog(content, **kwargs)
    dialog.render()

    if code is None:
        code = Other
    await wire.reply_message(session_id, ButtonRequest(code=code), ButtonAck)
    return await dialog == CONFIRMED


@unimport
async def hold_to_confirm(session_id, code=None):
    from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
    from trezor.ui.confirm import HoldToConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.wire_types import ButtonAck

    button = Button((0, 240 - 48, 240, 48), 'Hold to confirm',
                    normal_style=CONFIRM_BUTTON,
                    active_style=CONFIRM_BUTTON_ACTIVE)
    dialog = HoldToConfirmDialog(button)

    if code is None:
        code = Other
    await wire.reply_message(session_id, ButtonRequest(code=code), ButtonAck)
    return await dialog == CONFIRMED


@unimport
async def require_confirm(*args, **kwargs):
    from trezor.messages.FailureType import ActionCancelled

    confirmed = await confirm(*args, **kwargs)

    if not confirmed:
        raise wire.FailureError(ActionCancelled, 'Cancelled')
