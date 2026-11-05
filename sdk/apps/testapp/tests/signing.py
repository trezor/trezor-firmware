"""Host-side signing and key helpers, independent of the device."""

import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from ecdsa import NIST256p, SECP256k1, SigningKey, VerifyingKey
from ecdsa.curves import Curve
from ecdsa.ellipticcurve import PointJacobi
from ecdsa.util import sigdecode_string, sigencode_string_canonize

from .generated import messages as m

CURVES: dict[m.EcdsaCurve, Curve] = {
    m.EcdsaCurve.Secp256k1: SECP256k1,
    m.EcdsaCurve.Nist256p1: NIST256p,
}


def ecdsa_key(curve: m.EcdsaCurve, secret: int) -> SigningKey:
    return SigningKey.from_secret_exponent(
        secret, curve=CURVES[curve], hashfunc=hashlib.sha256
    )


def public_key(key: SigningKey, compressed: bool) -> bytes:
    vk = key.get_verifying_key()
    return vk.to_string("compressed" if compressed else "uncompressed")


def ecdsa_sign(key: SigningKey, digest: bytes) -> bytes:
    """A 64-byte r || s signature (low s) of `digest`."""
    return key.sign_digest_deterministic(
        digest, hashfunc=hashlib.sha256, sigencode=sigencode_string_canonize
    )


def recovery_id(
    curve: m.EcdsaCurve, public_key: bytes, rs: bytes, digest: bytes
) -> int:
    """The recovery id (R's y parity) under which `rs` recovers to `public_key`."""
    c = CURVES[curve]
    vk = VerifyingKey.from_string(public_key, curve=c)
    n, G = c.order, c.generator
    r, s = sigdecode_string(rs, n)
    e = int.from_bytes(digest, "big")
    p, a, b = c.curve.p(), c.curve.a(), c.curve.b()
    y2 = (pow(r, 3, p) + a * r + b) % p
    y = pow(y2, (p + 1) // 4, p)
    for parity in (0, 1):
        ry = y if y % 2 == parity else p - y
        R = PointJacobi(c.curve, r, ry, 1, n)
        Q = (R * s + G * ((-e) % n)) * pow(r, -1, n)
        if Q.to_affine() == vk.pubkey.point.to_affine():
            return parity
    raise ValueError("signature does not recover to the public key")


def ecdsa_verify(
    public_key: bytes, curve: m.EcdsaCurve, rs: bytes, digest: bytes
) -> bool:
    vk = VerifyingKey.from_string(public_key, curve=CURVES[curve])
    return vk.verify_digest(rs, digest, sigdecode=sigdecode_string)


def ed25519_key(seed: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(seed)


def ed25519_public_key(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
