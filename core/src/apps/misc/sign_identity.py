from typing import TYPE_CHECKING

from trezor.crypto.hashlib import sha256

from apps.common import coininfo

if TYPE_CHECKING:
    from trezor.messages import IdentityType, SignedIdentity, SignIdentity

    from apps.common.paths import Bip32Path

# This module implements the SLIP-0013 authentication using a deterministic hierarchy, see
# https://github.com/satoshilabs/slips/blob/master/slip-0013.md.


async def sign_identity(msg: SignIdentity) -> SignedIdentity:
    from trezor.messages import SignedIdentity
    from trezor.ui.layouts import confirm_sign_identity

    from apps.common.keychain import get_keychain
    from apps.common.paths import AlwaysMatchingSchema

    msg_identity = msg.identity  # local_cache_attribute
    msg_identity_proto = msg_identity.proto  # local_cache_attribute
    challenge_visual = msg.challenge_visual  # local_cache_attribute
    challenge_hidden = msg.challenge_hidden  # local_cache_attribute
    curve_name = msg.ecdsa_curve_name or "secp256k1"

    keychain = await get_keychain(curve_name, [AlwaysMatchingSchema])
    identity = serialize_identity(msg_identity)

    # require_confirm_sign_identity
    proto = msg_identity_proto.upper() if msg_identity_proto else "identity"
    await confirm_sign_identity(
        proto, serialize_identity_without_proto(msg_identity), challenge_visual
    )
    # END require_confirm_sign_identity

    address_n = get_identity_path(identity, msg_identity.index or 0, 13)
    node = keychain.derive(address_n)

    coin = coininfo.by_name("Bitcoin")
    if curve_name == "secp256k1":
        # hardcoded bitcoin address type
        address: str | None = node.address(coin.address_type)
    else:
        address = None
    pubkey = node.public_key()
    if pubkey[0] == 0x01:
        pubkey = b"\x00" + pubkey[1:]
    seckey = node.private_key()

    if msg_identity_proto in ("gpg", "signify", "ssh"):
        sigtype = msg_identity_proto
    else:
        sigtype = coin

    signature = sign_challenge(
        seckey,
        challenge_hidden,
        challenge_visual,
        sigtype,
        curve_name,
    )

    return SignedIdentity(address=address, public_key=pubkey, signature=signature)


def serialize_identity(identity: IdentityType) -> str:
    s = ""
    if identity.proto:
        s += identity.proto + "://"
    if identity.user:
        s += identity.user + "@"
    if identity.host:
        s += identity.host
    if identity.port:
        s += ":" + identity.port
    if identity.path:
        s += identity.path
    return s


def serialize_identity_without_proto(identity: IdentityType) -> str:
    proto = identity.proto
    identity.proto = None  # simplify serialized identity string
    s = serialize_identity(identity)
    identity.proto = proto
    return s


def get_identity_path(identity: str, index: int, num: int) -> Bip32Path:
    from ustruct import pack, unpack

    from apps.common.paths import HARDENED

    identity_hash = sha256(pack("<I", index) + identity.encode()).digest()

    return [HARDENED | x for x in (num,) + unpack("<IIII", identity_hash[:16])]


def sign_challenge(
    seckey: bytes,
    challenge_hidden: bytes,
    challenge_visual: str,
    sigtype: str | coininfo.CoinInfo,
    curve: str,
) -> bytes:
    from trezor.wire import DataError

    from apps.common.signverify import message_digest

    if sigtype == "gpg":
        data = challenge_hidden
    elif sigtype == "signify":
        if curve != "ed25519":
            raise DataError("Unsupported curve")
        data = challenge_hidden
    elif sigtype == "ssh":
        if curve != "ed25519":
            data = sha256(challenge_hidden).digest()
        else:
            data = challenge_hidden
    elif isinstance(sigtype, coininfo.CoinInfo):
        # sigtype is coin
        challenge = (
            sha256(challenge_hidden).digest()
            + sha256(challenge_visual.encode()).digest()
        )
        data = message_digest(sigtype, challenge)
    else:
        raise DataError("Unsupported sigtype")

    if curve == "secp256k1":
        from trezor.crypto.curve import secp256k1

        signature = secp256k1.sign(seckey, data)
    elif curve == "nist256p1":
        from trezor.crypto.curve import nist256p1

        signature = nist256p1.sign(seckey, data)
    elif curve == "ed25519":
        from trezor.crypto.curve import ed25519

        signature = ed25519.sign(seckey, data)
    else:
        raise DataError("Unknown curve")

    if curve == "ed25519":
        signature = b"\x00" + signature
    elif sigtype in ("gpg", "ssh"):
        signature = b"\x00" + signature[1:]

    return signature
