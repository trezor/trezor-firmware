from trezor import config, wire
from trezor.crypto import bip39
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.text import Text

from apps.common import storage
from apps.common.confirm import require_confirm


async def load_device(ctx, msg):

    if storage.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")

    if msg.node is not None:
        raise wire.ProcessError("LoadDevice.node is not supported")

    if not msg.skip_checksum and not bip39.check(msg.mnemonic):
        raise wire.ProcessError("Mnemonic is not valid")

    text = Text("Loading seed")
    text.bold("Loading private seed", "is not recommended.")
    text.normal("Continue only if you", "know what you are doing!")
    await require_confirm(ctx, text)

    storage.load_mnemonic(mnemonic=msg.mnemonic, needs_backup=True)
    storage.load_settings(use_passphrase=msg.passphrase_protection, label=msg.label)
    if msg.pin:
        config.change_pin(pin_to_int(""), pin_to_int(msg.pin), None)

    return Success(message="Device loaded")
