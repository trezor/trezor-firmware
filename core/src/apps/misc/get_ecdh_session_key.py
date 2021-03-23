from ustruct import pack, unpack

from trezor import ui, wire
from trezor.crypto.hashlib import sha256
from trezor.messages import ECDHSessionKey
from trezor.ui.layouts import confirm_hex

from apps.common import HARDENED
from apps.common.keychain import get_keychain
from apps.common.paths import AlwaysMatchingSchema

from .sign_identity import serialize_identity, serialize_identity_without_proto

if False:
    from trezor.messages import GetECDHSessionKey, IdentityType

    from apps.common.paths import Bip32Path

# This module implements the SLIP-0017 Elliptic Curve Diffie-Hellman algorithm, using a
# determinstic hierarchy, see https://github.com/satoshilabs/slips/blob/master/slip-0017.md.


async def get_ecdh_session_key(
    ctx: wire.Context, msg: GetECDHSessionKey
) -> ECDHSessionKey:
    if msg.ecdsa_curve_name is None:
        msg.ecdsa_curve_name = "secp256k1"

    keychain = await get_keychain(ctx, msg.ecdsa_curve_name, [AlwaysMatchingSchema])
    identity = serialize_identity(msg.identity)

    await require_confirm_ecdh_session_key(ctx, msg.identity)

    address_n = get_ecdh_path(identity, msg.identity.index or 0)
    node = keychain.derive(address_n)

    session_key = ecdh(
        seckey=node.private_key(),
        peer_public_key=msg.peer_public_key,
        curve=msg.ecdsa_curve_name,
    )
    return ECDHSessionKey(session_key=session_key, public_key=node.public_key())


async def require_confirm_ecdh_session_key(
    ctx: wire.Context, identity: IdentityType
) -> None:
    proto = identity.proto.upper() if identity.proto else "identity"
    await confirm_hex(
        ctx,
        "ecdh_session_key",
        "Decrypt %s" % proto,
        serialize_identity_without_proto(identity),
        icon=ui.ICON_DEFAULT,
        icon_color=ui.ORANGE_ICON,
    )


def get_ecdh_path(identity: str, index: int) -> Bip32Path:
    identity_hash = sha256(pack("<I", index) + identity.encode()).digest()

    address_n = [HARDENED | x for x in (17,) + unpack("<IIII", identity_hash[:16])]

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
            raise wire.DataError("Curve25519 public key should start with 0x40")
        session_key = b"\x04" + curve25519.multiply(seckey, peer_public_key[1:])
    else:
        raise wire.DataError("Unsupported curve for ECDH: " + curve)

    return session_key
