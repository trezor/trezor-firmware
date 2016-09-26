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
async def protect_with_confirm(*args, **kwargs):
    from trezor.messages.FailureType import ActionCancelled

    confirmed = await confirm(*args, **kwargs)

    if not confirmed:
        raise wire.FailureError(ActionCancelled, 'Cancelled')
