from trezor import wire
from trezor.utils import unimport


@unimport
async def confirm(content=None, code=None, **kwargs):
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.ButtonAck import ButtonAck

    dialog = ConfirmDialog(content, **kwargs)
    dialog.render()

    if code is None:
        code = Other
    ack = await wire.call(ButtonRequest(code=code), ButtonAck)
    res = await dialog.wait()

    return res == CONFIRMED
