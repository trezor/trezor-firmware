from trezor import ui, wire
from trezor.messages import ButtonRequestType, wire_types
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.FailureType import ActionCancelled, ProcessError
from trezor.messages.PassphraseRequest import PassphraseRequest
from trezor.ui.entry_select import DEVICE, EntrySelector
from trezor.ui.passphrase import CANCELLED, PassphraseKeyboard
from trezor.ui.text import Text
from apps.common import storage
from apps.common.cache import get_state


@ui.layout
async def request_passphrase_entry(ctx):
    text = Text(
        'Enter passphrase', ui.ICON_CONFIG,
        'Where to enter your', 'passphrase?')
    text.render()

    ack = await ctx.call(
        ButtonRequest(code=ButtonRequestType.PassphraseType),
        wire_types.ButtonAck,
        wire_types.Cancel)
    if ack.MESSAGE_WIRE_TYPE == wire_types.Cancel:
        raise wire.FailureError(ActionCancelled, 'Passphrase cancelled')

    selector = EntrySelector(text)
    return await ctx.wait(selector)


@ui.layout
async def request_passphrase_ack(ctx, on_device):
    if not on_device:
        text = Text(
            'Passphrase entry', ui.ICON_CONFIG,
            'Please, type passphrase', 'on connected host.')
        text.render()

    req = PassphraseRequest(on_device=on_device)
    ack = await ctx.call(req, wire_types.PassphraseAck, wire_types.Cancel)
    if ack.MESSAGE_WIRE_TYPE == wire_types.Cancel:
        raise wire.FailureError(ActionCancelled, 'Passphrase cancelled')

    if on_device:
        if ack.passphrase is not None:
            raise wire.FailureError(ProcessError, 'Passphrase provided when it should not be')
        keyboard = PassphraseKeyboard('Enter passphrase')
        passphrase = await ctx.wait(keyboard)
        if passphrase == CANCELLED:
            raise wire.FailureError(ActionCancelled, 'Passphrase cancelled')
    else:
        if ack.passphrase is None:
            raise wire.FailureError(ProcessError, 'Passphrase not provided')
        passphrase = ack.passphrase

    return ack.state, passphrase


async def request_passphrase(ctx):
    on_device = await request_passphrase_entry(ctx) == DEVICE
    state, passphrase = await request_passphrase_ack(ctx, on_device)
    if state is not None:
        if state != get_state(salt=state[:32], passphrase=passphrase):
            raise wire.FailureError(ProcessError, 'Passphrase mismatch')
    return passphrase


async def protect_by_passphrase(ctx):
    if storage.has_passphrase():
        return await request_passphrase(ctx)
    else:
        return ''
