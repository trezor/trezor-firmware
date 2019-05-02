from trezor import config, wire
from trezor.crypto import bip39
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.text import Text
from trezor.wire import errors

from apps.common import mnemonic, storage
from apps.common.confirm import require_confirm


async def load_device(ctx, msg):

    if storage.is_initialized():
        raise errors.UnexpectedMessage("Already initialized")

    if msg.node is not None:
        raise errors.ProcessError("LoadDevice.node is not supported")

    if not msg.skip_checksum and not bip39.check(msg.mnemonic):
        raise errors.ProcessError("Mnemonic is not valid")

    text = Text("Loading seed")
    text.bold("Loading private seed", "is not recommended.")
    text.normal("Continue only if you", "know what you are doing!")
    await require_confirm(ctx, text)

    secret = mnemonic.process([msg.mnemonic], mnemonic.TYPE_BIP39)
    storage.store_mnemonic(
        secret=secret,
        mnemonic_type=mnemonic.TYPE_BIP39,
        needs_backup=True,
        no_backup=False,
    )
    storage.load_settings(use_passphrase=msg.passphrase_protection, label=msg.label)
    if msg.pin:
        config.change_pin(pin_to_int(""), pin_to_int(msg.pin))

    return Success(message="Device loaded")
