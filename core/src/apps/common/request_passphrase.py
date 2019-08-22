from micropython import const

from trezor import ui, wire
from trezor.messages import ButtonRequestType, PassphraseSourceType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.PassphraseAck import PassphraseAck
from trezor.messages.PassphraseRequest import PassphraseRequest
from trezor.messages.PassphraseStateAck import PassphraseStateAck
from trezor.messages.PassphraseStateRequest import PassphraseStateRequest
from trezor.ui.passphrase import CANCELLED, PassphraseKeyboard, PassphraseSource
from trezor.ui.popup import Popup
from trezor.ui.text import Text

from apps.common import cache, storage

if __debug__:
    from apps.debug import input_signal

_MAX_PASSPHRASE_LEN = const(50)


async def protect_by_passphrase(ctx: wire.Context) -> str:
    if storage.device.has_passphrase():
        return await request_passphrase(ctx)
    else:
        return ""


async def request_passphrase(ctx: wire.Context) -> str:
    source = storage.device.get_passphrase_source()
    if source == PassphraseSourceType.ASK:
        source = await request_passphrase_source(ctx)
    passphrase = await request_passphrase_ack(
        ctx, source == PassphraseSourceType.DEVICE
    )
    if len(passphrase) > _MAX_PASSPHRASE_LEN:
        raise wire.DataError("Maximum passphrase length is %d" % _MAX_PASSPHRASE_LEN)
    return passphrase


async def request_passphrase_source(ctx: wire.Context) -> int:
    req = ButtonRequest(code=ButtonRequestType.PassphraseType)
    await ctx.call(req, ButtonAck)

    text = Text("Enter passphrase", ui.ICON_CONFIG)
    text.normal("Where to enter your", "passphrase?")
    source = PassphraseSource(text)

    return await ctx.wait(source)


async def request_passphrase_ack(ctx: wire.Context, on_device: bool) -> str:
    if not on_device:
        text = Text("Passphrase entry", ui.ICON_CONFIG)
        text.normal("Please, type passphrase", "on connected host.")
        await Popup(text)

    req = PassphraseRequest(on_device=on_device)
    ack = await ctx.call(req, PassphraseAck)

    if on_device:
        if ack.passphrase is not None:
            raise wire.ProcessError("Passphrase provided when it should not be")

        keyboard = PassphraseKeyboard("Enter passphrase", _MAX_PASSPHRASE_LEN)
        if __debug__:
            passphrase = await ctx.wait(keyboard, input_signal())
        else:
            passphrase = await ctx.wait(keyboard)
        if passphrase is CANCELLED:
            raise wire.ActionCancelled("Passphrase cancelled")
    else:
        if ack.passphrase is None:
            raise wire.ProcessError("Passphrase not provided")
        passphrase = ack.passphrase

    state = cache.get_state(prev_state=ack.state, passphrase=passphrase)
    req = PassphraseStateRequest(state=state)
    ack = await ctx.call(req, PassphraseStateAck)

    return passphrase
