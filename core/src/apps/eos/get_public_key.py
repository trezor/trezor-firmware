from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.messages.EosGetPublicKey import EosGetPublicKey
from trezor.messages.EosPublicKey import EosPublicKey

from apps.common import paths
from apps.eos import CURVE
from apps.eos.helpers import base58_encode, validate_full_path
from apps.eos.layout import require_get_public_key


def _public_key_to_wif(pub_key: bytes) -> str:
    if pub_key[0] == 0x04 and len(pub_key) == 65:
        head = b"\x03" if pub_key[64] & 0x01 else b"\x02"
        compressed_pub_key = head + pub_key[1:33]
    elif pub_key[0] in [0x02, 0x03] and len(pub_key) == 33:
        compressed_pub_key = pub_key
    else:
        raise wire.DataError("invalid public key")
    return base58_encode("PUB", compressed_pub_key)


def _get_public_key(node):
    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, True)
    wif = _public_key_to_wif(public_key)
    return wif, public_key


async def get_public_key(ctx, msg: EosGetPublicKey, keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    node = keychain.derive(msg.address_n)
    wif, public_key = _get_public_key(node)
    if msg.show_display:
        await require_get_public_key(ctx, wif)
    return EosPublicKey(wif, public_key)
