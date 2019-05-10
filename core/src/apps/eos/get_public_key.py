from trezor import wire
from trezor.crypto import base58
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import ripemd160
from trezor.messages.EosGetPublicKey import EosGetPublicKey
from trezor.messages.EosPublicKey import EosPublicKey

from apps.common import paths
from apps.eos import CURVE
from apps.eos.helpers import validate_full_path
from apps.eos.layout import require_get_public_key


def _ripemd160_32(data: bytes) -> bytes:
    return ripemd160(data).digest()[:4]


def _public_key_to_wif(pub_key: bytes) -> str:
    if len(pub_key) == 65:
        head = 0x03 if pub_key[64] & 0x01 else 0x02
        compresed_pub_key = bytes([head]) + pub_key[1:33]
    elif len(pub_key) == 33:
        compresed_pub_key = pub_key
    else:
        raise wire.DataError("invalid public key length")
    return "EOS" + base58.encode_check(compresed_pub_key, _ripemd160_32)


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
