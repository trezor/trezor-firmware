from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.messages.EosGetPublicKey import EosGetPublicKey
from trezor.messages.EosPublicKey import EosPublicKey

from apps.common import paths
from apps.eos import CURVE
from apps.eos.helpers import public_key_to_wif, validate_full_path
from apps.eos.layout import require_get_public_key

if False:
    from typing import Tuple
    from trezor.crypto import bip32
    from apps.common import seed


def _get_public_key(node: bip32.HDNode) -> Tuple[str, bytes]:
    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, True)
    wif = public_key_to_wif(public_key)
    return wif, public_key


async def get_public_key(
    ctx: wire.Context, msg: EosGetPublicKey, keychain: seed.Keychain
) -> EosPublicKey:
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n)
    wif, public_key = _get_public_key(node)
    if msg.show_display:
        await require_get_public_key(ctx, wif)
    return EosPublicKey(wif, public_key)
