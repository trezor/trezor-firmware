from micropython import const

import storage.device
from trezor import wire, workflow
from trezor.messages import ButtonRequestType

from . import button_request

_MAX_PASSPHRASE_LEN = const(50)


def is_enabled() -> bool:
    return storage.device.is_passphrase_enabled()


async def get(ctx: wire.Context) -> str:
    if is_enabled():
        return await _request_from_user(ctx)
    else:
        return ""


async def _request_from_user(ctx: wire.Context) -> str:
    workflow.close_others()  # request exclusive UI access
    if storage.device.get_passphrase_always_on_device():
        passphrase = await _request_on_device(ctx)
    else:
        passphrase = await _request_on_host(ctx)
    if len(passphrase.encode()) > _MAX_PASSPHRASE_LEN:
        raise wire.DataError(
            "Maximum passphrase length is %d bytes" % _MAX_PASSPHRASE_LEN
        )

    return passphrase


async def _request_on_host(ctx: wire.Context) -> str:
    from trezor.messages.PassphraseAck import PassphraseAck
    from trezor.messages.PassphraseRequest import PassphraseRequest
    from trezor.ui import ICON_CONFIG
    from trezor.ui.components.tt.text import Text

    from .confirm import require_confirm

    _entry_dialog()

    request = PassphraseRequest()
    ack = await ctx.call(request, PassphraseAck)
    if ack.on_device:
        if ack.passphrase is not None:
            raise wire.DataError("Passphrase provided when it should not be")
        return await _request_on_device(ctx)

    if ack.passphrase is None:
        raise wire.DataError(
            "Passphrase not provided and on_device is False. Use empty string to set an empty passphrase."
        )

    # non-empty passphrase
    if ack.passphrase:
        text = Text("Hidden wallet", ICON_CONFIG)
        text.normal("Access hidden wallet?")
        text.br()
        text.normal("Next screen will show")
        text.normal("the passphrase!")
        await require_confirm(ctx, text, ButtonRequestType.Other)

        text = Text("Hidden wallet", ICON_CONFIG, break_words=True)
        text.normal("Use this passphrase?")
        text.br()
        text.mono(ack.passphrase)
        await require_confirm(ctx, text, ButtonRequestType.Other)

    return ack.passphrase


async def _request_on_device(ctx: wire.Context) -> str:
    from trezor.ui.components.tt.passphrase import CANCELLED, PassphraseKeyboard

    await button_request(ctx, code=ButtonRequestType.PassphraseEntry)

    keyboard = PassphraseKeyboard("Enter passphrase", _MAX_PASSPHRASE_LEN)
    passphrase = await ctx.wait(keyboard)
    if passphrase is CANCELLED:
        raise wire.ActionCancelled("Passphrase entry cancelled")

    assert isinstance(passphrase, str)

    return passphrase


def _entry_dialog() -> None:
    from trezor.ui import ICON_CONFIG, draw_simple
    from trezor.ui.components.tt.text import Text

    text = Text("Passphrase entry", ICON_CONFIG)
    text.normal("Please type your", "passphrase on the", "connected host.")
    draw_simple(text)
