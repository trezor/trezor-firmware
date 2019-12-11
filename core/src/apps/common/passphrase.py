from micropython import const

import storage.device
from trezor import wire
from trezor.messages import ButtonRequestType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.PassphraseAck import PassphraseAck
from trezor.messages.PassphraseRequest import PassphraseRequest
from trezor.ui.passphrase import CANCELLED, PassphraseKeyboard

if __debug__:
    from apps.debug import input_signal

_MAX_PASSPHRASE_LEN = const(50)


def is_enabled() -> bool:
    return storage.device.is_passphrase_enabled()


async def get(ctx: wire.Context) -> str:
    if is_enabled():
        return await request_from_user(ctx)
    else:
        return ""


async def request_from_user(ctx: wire.Context) -> str:
    request = PassphraseRequest()
    ack = await ctx.call(request, PassphraseAck)
    if ack.on_device:
        if ack.passphrase is not None:
            raise wire.ProcessError("Passphrase provided when it should not be")
        passphrase = await request_from_user_on_device(ctx)
    else:
        if ack.passphrase is None:
            raise wire.ProcessError("Passphrase not provided")
        passphrase = ack.passphrase

    if len(passphrase) > _MAX_PASSPHRASE_LEN:
        raise wire.DataError("Maximum passphrase length is %d" % _MAX_PASSPHRASE_LEN)

    return passphrase


async def request_from_user_on_device(ctx: wire.Context) -> str:
    await ctx.call(ButtonRequest(code=ButtonRequestType.PassphraseEntry), ButtonAck)

    keyboard = PassphraseKeyboard("Enter passphrase", _MAX_PASSPHRASE_LEN)
    if __debug__:
        passphrase = await ctx.wait(keyboard, input_signal())
    else:
        passphrase = await ctx.wait(keyboard)
    if passphrase is CANCELLED:
        raise wire.ActionCancelled("Passphrase entry cancelled")

    assert isinstance(passphrase, str)

    return passphrase
