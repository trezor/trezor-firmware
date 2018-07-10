from trezor import ui, wire
from trezor.messages import ButtonRequestType, PassphraseSourceType
from trezor.messages.Success import Success
from trezor.ui.text import Text

from apps.common import storage
from apps.common.confirm import require_confirm


async def apply_settings(ctx, msg):
    if (
        msg.homescreen is None
        and msg.label is None
        and msg.use_passphrase is None
        and msg.passphrase_source is None
    ):
        raise wire.ProcessError("No setting provided")

    if msg.homescreen is not None:
        if len(msg.homescreen) > storage.HOMESCREEN_MAXSIZE:
            raise wire.DataError("Homescreen is too complex")
        await require_confirm_change_homescreen(ctx)

    if msg.label is not None:
        await require_confirm_change_label(ctx, msg.label)

    if msg.use_passphrase is not None:
        await require_confirm_change_passphrase(ctx, msg.use_passphrase)

    if msg.passphrase_source is not None:
        await require_confirm_change_passphrase_source(ctx, msg.passphrase_source)

    storage.load_settings(
        label=msg.label,
        use_passphrase=msg.use_passphrase,
        homescreen=msg.homescreen,
        passphrase_source=msg.passphrase_source,
    )

    return Success(message="Settings applied")


async def require_confirm_change_homescreen(ctx):
    text = Text("Change homescreen", ui.ICON_CONFIG)
    text.normal("Do you really want to", "change homescreen?")
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)


async def require_confirm_change_label(ctx, label):
    text = Text("Change label", ui.ICON_CONFIG)
    text.normal("Do you really want to", "change label to")
    text.bold("%s?" % label)
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)


async def require_confirm_change_passphrase(ctx, use):
    text = Text("Enable passphrase" if use else "Disable passphrase", ui.ICON_CONFIG)
    text.normal("Do you really want to")
    text.normal("enable passphrase" if use else "disable passphrase")
    text.normal("encryption?")
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)


async def require_confirm_change_passphrase_source(ctx, source):
    if source == PassphraseSourceType.DEVICE:
        desc = "ON DEVICE"
    elif source == PassphraseSourceType.HOST:
        desc = "ON HOST"
    else:
        desc = "ASK"
    text = Text("Passphrase source", ui.ICON_CONFIG)
    text.normal("Do you really want to", "change the passphrase", "source to")
    text.bold("ALWAYS %s?" % desc)
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)
