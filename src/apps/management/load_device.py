from trezor import config, ui, wire
from trezor.crypto import bip39
from trezor.messages.FailureType import ProcessError, UnexpectedMessage
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.text import Text
from apps.common import storage
from apps.common.confirm import require_confirm


async def load_device(ctx, msg):

    if storage.is_initialized():
        raise wire.FailureError(UnexpectedMessage, 'Already initialized')

    if msg.node is not None:
        raise wire.FailureError(ProcessError, 'LoadDevice.node is not supported')

    if not msg.skip_checksum and not bip39.check(msg.mnemonic):
        raise wire.FailureError(ProcessError, 'Mnemonic is not valid')

    await require_confirm(ctx, Text(
        'Loading seed', ui.ICON_DEFAULT,
        ui.BOLD, 'Loading private seed', 'is not recommended.',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'))

    storage.load_mnemonic(
        mnemonic=msg.mnemonic, needs_backup=True)
    storage.load_settings(
        use_passphrase=msg.passphrase_protection, label=msg.label)
    if msg.pin:
        config.change_pin(pin_to_int(''), pin_to_int(msg.pin), None)

    return Success(message='Device loaded')
