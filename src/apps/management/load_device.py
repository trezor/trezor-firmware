from trezor import wire, ui, config
from trezor.pin import pin_to_int
from trezor.utils import unimport


@unimport
async def layout_load_device(ctx, msg):
    from trezor.crypto import bip39
    from trezor.messages.Success import Success
    from trezor.messages.FailureType import UnexpectedMessage, ProcessError
    from trezor.ui.text import Text
    from ..common.confirm import require_confirm
    from ..common import storage

    if storage.is_initialized():
        raise wire.FailureError(UnexpectedMessage, 'Already initialized')

    if msg.node is not None:
        raise wire.FailureError(ProcessError, 'LoadDevice.node is not supported')

    if not msg.skip_checksum and not bip39.check(msg.mnemonic):
        raise wire.FailureError(ProcessError, 'Mnemonic is not valid')

    await require_confirm(ctx, Text(
        'Loading seed', ui.ICON_RESET,
        ui.BOLD, 'Loading private seed', 'is not recommended.',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'))

    storage.load_mnemonic(msg.mnemonic)
    storage.load_settings(use_passphrase=msg.passphrase_protection,
                          label=msg.label)
    if msg.pin:
        config.change_pin(pin_to_int(''), pin_to_int(msg.pin), None)

    return Success(message='Device loaded')
