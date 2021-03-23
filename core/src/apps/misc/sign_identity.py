from ustruct import pack, unpack

from trezor import wire
from trezor.crypto.hashlib import sha256
from trezor.messages import SignedIdentity
from trezor.ui.layouts import confirm_sign_identity

from apps.common import HARDENED, coininfo
from apps.common.keychain import get_keychain
from apps.common.paths import AlwaysMatchingSchema

if False:
    from trezor.messages import IdentityType, SignIdentity

    from apps.common.paths import Bip32Path

# This module implements the SLIP-0013 authentication using a deterministic hierarchy, see
# https://github.com/satoshilabs/slips/blob/master/slip-0013.md.


async def sign_identity(ctx: wire.Context, msg: SignIdentity) -> SignedIdentity:
    if msg.ecdsa_curve_name is None:
        msg.ecdsa_curve_name = "secp256k1"

    keychain = await get_keychain(ctx, msg.ecdsa_curve_name, [AlwaysMatchingSchema])
    identity = serialize_identity(msg.identity)

    await require_confirm_sign_identity(ctx, msg.identity, msg.challenge_visual)

    address_n = get_identity_path(identity, msg.identity.index or 0)
    node = keychain.derive(address_n)

    coin = coininfo.by_name("Bitcoin")
    if msg.ecdsa_curve_name == "secp256k1":
        # hardcoded bitcoin address type
        address: str | None = node.address(coin.address_type)
    else:
        address = None
    pubkey = node.public_key()
    if pubkey[0] == 0x01:
        pubkey = b"\x00" + pubkey[1:]
    seckey = node.private_key()

    if msg.identity.proto == "gpg":
        signature = sign_challenge(
            seckey,
            msg.challenge_hidden,
            msg.challenge_visual,
            "gpg",
            msg.ecdsa_curve_name,
        )
    elif msg.identity.proto == "signify":
        signature = sign_challenge(
            seckey,
            msg.challenge_hidden,
            msg.challenge_visual,
            "signify",
            msg.ecdsa_curve_name,
        )
    elif msg.identity.proto == "ssh":
        signature = sign_challenge(
            seckey,
            msg.challenge_hidden,
            msg.challenge_visual,
            "ssh",
            msg.ecdsa_curve_name,
        )
    else:
        signature = sign_challenge(
            seckey,
            msg.challenge_hidden,
            msg.challenge_visual,
            coin,
            msg.ecdsa_curve_name,
        )

    return SignedIdentity(address=address, public_key=pubkey, signature=signature)


async def require_confirm_sign_identity(
    ctx: wire.Context, identity: IdentityType, challenge_visual: str | None
) -> None:
    proto = identity.proto.upper() if identity.proto else "identity"
    await confirm_sign_identity(
        ctx, proto, serialize_identity_without_proto(identity), challenge_visual
    )


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


def get_identity_path(identity: str, index: int) -> Bip32Path:
    identity_hash = sha256(pack("<I", index) + identity.encode()).digest()

    address_n = [HARDENED | x for x in (13,) + unpack("<IIII", identity_hash[:16])]

    return address_n


def sign_challenge(
    seckey: bytes,
    challenge_hidden: bytes,
    challenge_visual: str,
    sigtype: str | coininfo.CoinInfo,
    curve: str,
) -> bytes:
    from trezor.crypto.hashlib import sha256

    if curve == "secp256k1":
        from trezor.crypto.curve import secp256k1
    elif curve == "nist256p1":
        from trezor.crypto.curve import nist256p1
    elif curve == "ed25519":
        from trezor.crypto.curve import ed25519
    from apps.common.signverify import message_digest

    if sigtype == "gpg":
        data = challenge_hidden
    elif sigtype == "signify":
        if curve != "ed25519":
            raise wire.DataError("Unsupported curve")
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
        raise wire.DataError("Unsupported sigtype")

    if curve == "secp256k1":
        signature = secp256k1.sign(seckey, data)
    elif curve == "nist256p1":
        signature = nist256p1.sign(seckey, data)
    elif curve == "ed25519":
        signature = ed25519.sign(seckey, data)
    else:
        raise wire.DataError("Unknown curve")

    if curve == "ed25519":
        signature = b"\x00" + signature
    elif sigtype == "gpg" or sigtype == "ssh":
        signature = b"\x00" + signature[1:]

    return signature
