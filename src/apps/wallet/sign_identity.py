from typing import List

from trezor import ui
from trezor.utils import unimport


def serialize_identity(identity):
    s = ''
    if identity.proto:
        s += identity.proto + '://'
    if identity.user:
        s += identity.user + '@'
    if identity.host:
        s += identity.host
    if identity.port:
        s += ':' + identity.port
    if identity.path:
        s += identity.path
    return s


def display_identity(identity: str, challenge_visual: str):
    ui.display.clear()
    ui.display.text(10, 30, 'Identity:',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, challenge_visual, ui.MONO, ui.WHITE, ui.BLACK)
    ui.display.text(10, 80, identity, ui.MONO, ui.WHITE, ui.BLACK)


def get_identity_path(identity: str, index: int) -> List[int]:
    from ustruct import pack, unpack
    from trezor.crypto.hashlib import sha256

    identity_hash = sha256(pack('<I', index) + identity).digest()

    address_n = (13, ) + unpack('<IIII', identity_hash[:16])
    address_n = [0x80000000 | x for x in address_n]

    return address_n


def sign_challenge(seckey: bytes,
                   challenge_hidden: bytes,
                   challenge_visual: str,
                   coin) -> bytes:
    from trezor.crypto.hashlib import sha256
    from trezor.crypto.curve import secp256k1
    from ..common.signverify import message_digest

    challenge = sha256(challenge_hidden).digest() + \
        sha256(challenge_visual).digest()
    digest = message_digest(coin, challenge)
    signature = secp256k1.sign(seckey, digest)

    return signature


@unimport
async def layout_sign_identity(session_id, msg):
    from trezor.messages.SignedIdentity import SignedIdentity
    from ..common import coins
    from ..common import seed

    identity = serialize_identity(msg.identity)
    display_identity(identity, msg.challenge_visual)

    address_n = get_identity_path(identity, msg.identity.index or 0)
    node = await seed.get_root(session_id, msg.ecdsa_curve_name)
    node.derive_path(address_n)

    coin = coins.by_name('Bitcoin')
    address = node.address(coin.address_type)  # hardcoded bitcoin address type
    pubkey = node.public_key()
    seckey = node.private_key()

    signature = sign_challenge(
        seckey, msg.challenge_hidden, msg.challenge_visual, coin)

    return SignedIdentity(address=address, public_key=pubkey, signature=signature)
