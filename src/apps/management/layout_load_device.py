from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_load_device(message, session_id):
    from trezor.messages.Storage import Storage
    from trezor.messages.Success import Success
    from trezor.messages.FailureType import UnexpectedMessage, Other
    from trezor.ui.text import Text
    from ..common.storage import get_storage, set_storage
    from ..common.confirm import require_confirm

    if get_storage(session_id):
        raise wire.FailureError(UnexpectedMessage, 'Already initialized')

    ui.display.clear()

    await require_confirm(session_id, Text(
        'Loading seed',
        ui.BOLD, 'Loading private seed', 'is not recommended.',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'))

    node = getattr(message, 'node', None)
    mnemonic = getattr(message, 'mnemonic', None)

    # if node is not None:
    #     raise wire.FailureError(Other, 'XPRV import is not implemented')
    # if mnemonic is not None and not message.skip_checksum:
    #     raise wire.FailureError(Other, 'Mnemonic checksum is not implemented')

    storage = Storage(
        version=1, imported=1, mnemonic=mnemonic, node=node,
        pin=message.pin, passphrase_protection=message.passphrase_protection,
        language=message.language, label=message.label)
    set_storage(session_id, await storage.dumps())

    return Success(message='Device loaded')
