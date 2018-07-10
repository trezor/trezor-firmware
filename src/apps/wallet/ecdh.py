from ustruct import pack, unpack

from trezor.crypto.hashlib import sha256
from trezor.messages.ECDHSessionKey import ECDHSessionKey
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common import HARDENED, seed
from apps.common.confirm import require_confirm
from apps.wallet.sign_identity import (
    serialize_identity,
    serialize_identity_without_proto,
)


async def get_ecdh_session_key(ctx, msg):
    if msg.ecdsa_curve_name is None:
        msg.ecdsa_curve_name = "secp256k1"

    identity = serialize_identity(msg.identity)

    await require_confirm_ecdh_session_key(ctx, msg.identity)

    address_n = get_ecdh_path(identity, msg.identity.index or 0)
    node = await seed.derive_node(ctx, address_n, msg.ecdsa_curve_name)

    session_key = ecdh(
        seckey=node.private_key(),
        peer_public_key=msg.peer_public_key,
        curve=msg.ecdsa_curve_name,
    )
    return ECDHSessionKey(session_key=session_key)


async def require_confirm_ecdh_session_key(ctx, identity):
    lines = chunks(serialize_identity_without_proto(identity), 18)
    proto = identity.proto.upper() if identity.proto else "identity"
    text = Text("Decrypt %s" % proto)
    text.mono(*lines)
    await require_confirm(ctx, text)


def get_ecdh_path(identity: str, index: int):
    identity_hash = sha256(pack("<I", index) + identity).digest()

    address_n = (17,) + unpack("<IIII", identity_hash[:16])
    address_n = [HARDENED | x for x in address_n]

    return address_n


def ecdh(seckey: bytes, peer_public_key: bytes, curve: str) -> bytes:
    if curve == "secp256k1":
        from trezor.crypto.curve import secp256k1

        session_key = secp256k1.multiply(seckey, peer_public_key)
    elif curve == "nist256p1":
        from trezor.crypto.curve import nist256p1

        session_key = nist256p1.multiply(seckey, peer_public_key)
    elif curve == "curve25519":
        from trezor.crypto.curve import curve25519

        if peer_public_key[0] != 0x40:
            raise ValueError("Curve25519 public key should start with 0x40")
        session_key = b"\x04" + curve25519.multiply(seckey, peer_public_key[1:])
    else:
        raise ValueError("Unsupported curve for ECDH: " + curve)

    return session_key
