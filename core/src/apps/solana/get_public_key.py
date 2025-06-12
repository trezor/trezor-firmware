from typing import TYPE_CHECKING

from trezor.crypto import base58

from apps.common import seed
from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import SolanaGetPublicKey, SolanaPublicKey

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_public_key(
    msg: SolanaGetPublicKey, keychain: Keychain
) -> SolanaPublicKey:
    from trezor.messages import SolanaPublicKey
    from trezor.ui.layouts import show_pubkey

    public_key = derive_public_key(keychain, msg.address_n)

    if msg.show_display:
        from apps.common.paths import address_n_to_str

        path = address_n_to_str(msg.address_n)
        await show_pubkey(base58.encode(public_key), path=path)

    return SolanaPublicKey(public_key=public_key)


def derive_public_key(keychain: Keychain, address_n: list[int]) -> bytes:
    node = keychain.derive(address_n)
    return seed.remove_ed25519_prefix(node.public_key())
