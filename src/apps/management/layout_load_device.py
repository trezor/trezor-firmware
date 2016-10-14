from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_load_device(message, session_id):
    from trezor.crypto import bip39
    from trezor.messages.Success import Success
    from trezor.messages.FailureType import UnexpectedMessage, Other
    from trezor.ui.text import Text
    from ..common.confirm import require_confirm
    from ..common import storage

    if storage.is_initialized():
        raise wire.FailureError(UnexpectedMessage, 'Already initialized')

    if not message.skip_checksum and not bip39.check(message.mnemonic):
        raise wire.FailureError(Other, 'Mnemonic is not valid')

    await require_confirm(session_id, Text(
        'Loading seed',
        ui.BOLD, 'Loading private seed', 'is not recommended.',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'))

    storage.load_mnemonic(message.mnemonic)
    storage.load_settings(pin=message.pin,
                          passphrase_protection=message.passphrase_protection,
                          language=message.language,
                          label=message.label)

    return Success(message='Device loaded')
