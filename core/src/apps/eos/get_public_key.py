from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import EosGetPublicKey, EosPublicKey
    from trezor.wire import MaybeEarlyResponse

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_public_key(
    msg: EosGetPublicKey, keychain: Keychain
) -> MaybeEarlyResponse[EosPublicKey]:
    from trezor.crypto.curve import secp256k1
    from trezor.messages import EosPublicKey
    from trezor.ui.layouts import show_continue_in_app
    from trezor.wire import early_response

    from apps.common import paths

    from .helpers import public_key_to_wif
    from .layout import require_get_public_key

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)

    public_key = secp256k1.publickey(node.private_key(), True)
    wif = public_key_to_wif(public_key)
    response = EosPublicKey(wif_public_key=wif, raw_public_key=public_key)

    if msg.show_display:
        from trezor import TR

        from . import PATTERN, SLIP44_ID

        path = paths.address_n_to_str(msg.address_n)
        account = paths.get_account_name("EOS", msg.address_n, PATTERN, SLIP44_ID)
        await require_get_public_key(wif, path, account)
        return await early_response(
            response, show_continue_in_app(TR.address__public_key_confirmed)
        )

    return response
