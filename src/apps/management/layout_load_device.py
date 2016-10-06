from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_load_device(message, session_id):
    from trezor.crypto import bip39
    from trezor.messages.Storage import Storage
    from trezor.messages.Success import Success
    from trezor.messages.FailureType import UnexpectedMessage, Other
    from trezor.ui.text import Text
    from ..common.confirm import require_confirm
    from ..common import storage

    if storage.has(session_id):
        raise wire.FailureError(UnexpectedMessage, 'Already initialized')

    st = Storage()
    st.imported = True
    st.version = 1
    st.pin = message.pin
    st.passphrase_protection = message.passphrase_protection,
    st.language = message.language
    st.label = message.label

    if hasattr(message, 'node'):
        st.node = message.node

    elif hasattr(message, 'mnemonic'):
        st.mnemonic = message.mnemonic
        if not message.skip_checksum and not bip39.check(message.mnemonic):
            raise wire.FailureError(Other, 'Mnemonic is not valid')

    await require_confirm(session_id, Text(
        'Loading seed',
        ui.BOLD, 'Loading private seed', 'is not recommended.',
        ui.NORMAL, 'Continue only if you', 'know what you are doing!'))

    storage.set(session_id, st)

    return Success(message='Device loaded')
