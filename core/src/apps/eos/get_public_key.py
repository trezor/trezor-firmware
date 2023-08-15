from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import EosGetPublicKey, EosPublicKey

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_public_key(msg: EosGetPublicKey, keychain: Keychain) -> EosPublicKey:
    from trezor.crypto.curve import secp256k1
    from trezor.messages import EosPublicKey

    from apps.common import paths

    from .helpers import public_key_to_wif
    from .layout import require_get_public_key

    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)

    public_key = secp256k1.publickey(node.private_key(), True)
    wif = public_key_to_wif(public_key)

    if msg.show_display:
        await require_get_public_key(wif)
    return EosPublicKey(wif_public_key=wif, raw_public_key=public_key)
