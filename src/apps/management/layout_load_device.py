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

    if hasattr(message, 'node'):
        raise wire.FailureError(Other, 'LoadDevice.node is not supported')

    skip_checksum = getattr(message, 'skip_checksum', False)
    mnemonic = getattr(message, 'mnemonic')
    pin = getattr(message, 'pin', None)
    label = getattr(message, 'label', None)
    language = getattr(message, 'language', None)
    passphrase_protection = getattr(message, 'passphrase_protection', False)

    if not skip_checksum and not bip39.check(mnemonic):
        raise wire.FailureError(Other, 'Mnemonic is not valid')

    await require_confirm(session_id, Text(
        'Loading seed', ui.ICON_RESET,
        ui.BOLD, 'Loading private seed', 'is not recommended.',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'))

    storage.load_mnemonic(mnemonic)
    storage.load_settings(pin=pin,
                          passphrase_protection=passphrase_protection,
                          language=language,
                          label=label)

    return Success(message='Device loaded')
