from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_load_device(message, session_id):
    from trezor.crypto import bip39
    from trezor.messages.Storage import Storage
    from trezor.messages.Success import Success
    from trezor.messages.FailureType import UnexpectedMessage, Other
    from trezor.ui.text import Text
    from ..common.storage import get_storage, set_storage
    from ..common.confirm import require_confirm

    if get_storage(session_id):
        raise wire.FailureError(UnexpectedMessage, 'Already initialized')
    storage = Storage()
    storage.imported = True

    if hasattr(message, 'node'):
        storage.node = message.node
    elif hasattr(message, 'mnemonic'):
        if not message.skip_checksum and not bip39.check(message.mnemonic):
            raise wire.FailureError(Other, 'Mnemonic is not valid')
        storage.mnemonic = message.mnemonic

    ui.display.clear()

    await require_confirm(session_id, Text(
        'Loading seed',
        ui.BOLD, 'Loading private seed', 'is not recommended.',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'))

    storage.version = 1
    storage.pin = message.pin
    storage.passphrase_protection = message.passphrase_protection,
    storage.language = message.language
    storage.label = message.label

    set_storage(session_id, await storage.dumps())

    return Success(message='Device loaded')
