from ustruct import pack, unpack

from trezor import ui
from trezor.crypto.hashlib import sha256
from trezor.messages.SignedIdentity import SignedIdentity
from trezor.utils import chunks
from trezor.ui.text import Text

from apps.common import coins, seed, HARDENED
from apps.common.confirm import require_confirm


async def sign_identity(ctx, msg):
    if msg.ecdsa_curve_name is None:
        msg.ecdsa_curve_name = 'secp256k1'

    identity = serialize_identity(msg.identity)

    await require_confirm_sign_identity(ctx, msg.identity, msg.challenge_visual)

    address_n = get_identity_path(identity, msg.identity.index or 0)
    node = await seed.derive_node(ctx, address_n, msg.ecdsa_curve_name)

    coin = coins.by_name('Bitcoin')
    if msg.ecdsa_curve_name == 'secp256k1':
        address = node.address(coin.address_type)  # hardcoded bitcoin address type
    else:
        address = None
    pubkey = node.public_key()
    if pubkey[0] == 0x01:
        pubkey = b'\x00' + pubkey[1:]
    seckey = node.private_key()

    if msg.identity.proto == 'gpg':
        signature = sign_challenge(
            seckey, msg.challenge_hidden, msg.challenge_visual, 'gpg', msg.ecdsa_curve_name)
    elif msg.identity.proto == 'ssh':
        signature = sign_challenge(
            seckey, msg.challenge_hidden, msg.challenge_visual, 'ssh', msg.ecdsa_curve_name)
    else:
        signature = sign_challenge(
            seckey, msg.challenge_hidden, msg.challenge_visual, coin, msg.ecdsa_curve_name)

    return SignedIdentity(address=address, public_key=pubkey, signature=signature)


async def require_confirm_sign_identity(ctx, identity, challenge_visual):
    lines = []
    if challenge_visual:
        lines.append(challenge_visual)

    lines.append(ui.MONO)
    lines.extend(chunks(serialize_identity_without_proto(identity), 18))

    proto = identity.proto.upper() if identity.proto else 'identity'
    header = 'Sign %s' % proto
    content = Text(header, ui.ICON_DEFAULT, *lines, max_lines=5)
    await require_confirm(ctx, content)


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


def serialize_identity_without_proto(identity):
    proto = identity.proto
    identity.proto = None  # simplify serialized identity string
    s = serialize_identity(identity)
    identity.proto = proto
    return s


def get_identity_path(identity: str, index: int):
    identity_hash = sha256(pack('<I', index) + identity).digest()

    address_n = (13, ) + unpack('<IIII', identity_hash[:16])
    address_n = [HARDENED | x for x in address_n]

    return address_n


def sign_challenge(seckey: bytes,
                   challenge_hidden: bytes,
                   challenge_visual: str,
                   sigtype,
                   curve: str) -> bytes:
    from trezor.crypto.hashlib import sha256
    if curve == 'secp256k1':
        from trezor.crypto.curve import secp256k1
    elif curve == 'nist256p1':
        from trezor.crypto.curve import nist256p1
    elif curve == 'ed25519':
        from trezor.crypto.curve import ed25519
    from apps.common.signverify import message_digest

    if sigtype == 'gpg':
        data = challenge_hidden
    elif sigtype == 'ssh':
        if curve != 'ed25519':
            data = sha256(challenge_hidden).digest()
        else:
            data = challenge_hidden
    else:
        # sigtype is coin
        challenge = sha256(challenge_hidden).digest() + sha256(challenge_visual).digest()
        data = message_digest(sigtype, challenge)

    if curve == 'secp256k1':
        signature = secp256k1.sign(seckey, data)
    elif curve == 'nist256p1':
        signature = nist256p1.sign(seckey, data)
    elif curve == 'ed25519':
        signature = ed25519.sign(seckey, data)
    else:
        raise ValueError('Unknown curve')

    if curve == 'ed25519':
        signature = b'\x00' + signature
    elif sigtype == 'gpg' or sigtype == 'ssh':
        signature = b'\x00' + signature[1:]

    return signature
