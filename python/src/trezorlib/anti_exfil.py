from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

import ecdsa


@dataclass
class AntiExfilSignature:
    signature: bytes
    entropy: Optional[bytes]
    nonce_commitment: Optional[bytes]


def generate_entropy() -> bytes:
    import os

    return os.urandom(32)


def sha256_data(message: bytes) -> bytes:
    # https://github.com/BlockstreamResearch/secp256k1-zkp/blob/6152622613fdf1c5af6f31f74c427c4e9ee120ce/src/modules/ecdsa_s2c/main_impl.h#L54
    tag = b"s2c/ecdsa/data"
    tag_digest = sha256(tag).digest()
    return sha256(tag_digest + tag_digest + message).digest()


def commit_entropy(entropy: bytes) -> bytes:
    # https://github.com/BlockstreamResearch/secp256k1-zkp/blob/6152622613fdf1c5af6f31f74c427c4e9ee120ce/src/modules/ecdsa_s2c/main_impl.h#L140
    return sha256_data(entropy)


def sha256_point(message: bytes) -> bytes:
    # https://github.com/BlockstreamResearch/secp256k1-zkp/blob/6152622613fdf1c5af6f31f74c427c4e9ee120ce/src/modules/ecdsa_s2c/main_impl.h#L38
    tag = b"s2c/ecdsa/point"
    tag_digest = sha256(tag).digest()
    return sha256(tag_digest + tag_digest + message).digest()


def tweak_nonce(nonce_commitment: bytes, entropy: bytes) -> bytes:
    # https://github.com/BlockstreamResearch/secp256k1-zkp/blob/6152622613fdf1c5af6f31f74c427c4e9ee120ce/src/eccommit_impl.h#L42
    tweak = sha256_point(nonce_commitment + entropy)
    return tweak_public_key(nonce_commitment, tweak)[1:]


def verify(
    public_key: Optional[bytes],
    signature: bytes,
    digest: Optional[bytes],
    entropy: bytes,
    nonce_commitment: bytes,
) -> bool:
    # https://github.com/BlockstreamResearch/secp256k1-zkp/blob/6152622613fdf1c5af6f31f74c427c4e9ee120ce/src/modules/ecdsa_s2c/main_impl.h#L192
    # The three conditions must be satisfied to succeed in the verification:
    #   1. The signature must be valid. This check is performed only if the public key and the digest are provided.
    #   2. The r value of the signature must include the host's entropy.
    #   3. The s value of the signature must be less than the half of the curve's order.
    # A malicious trezor can always generate signature that:
    #   1. Satisfies two of the three conditions above.
    #   2. Can be used to leak information about trezor's seed.

    # https://github.com/BlockstreamResearch/secp256k1-zkp/blob/6152622613fdf1c5af6f31f74c427c4e9ee120ce/src/secp256k1.c#L442
    if public_key is not None and digest is not None:
        if not ecdsa.verify(digest, signature, public_key):
            return False

    # https://github.com/BlockstreamResearch/secp256k1-zkp/blob/6152622613fdf1c5af6f31f74c427c4e9ee120ce/src/modules/ecdsa_s2c/main_impl.h#L98
    r_bytes = signature[:32]
    if r_bytes != tweak_nonce(nonce_commitment, entropy):
        return False

    # https://github.com/BlockstreamResearch/secp256k1-zkp/blob/6152622613fdf1c5af6f31f74c427c4e9ee120ce/src/scalar_4x64_impl.h#L255
    s_bytes = signature[32:64]
    s = int.from_bytes(s_bytes, byteorder="big")
    if s > ecdsa.SECP256k1.order // 2:
        return False

    return True


# Returns point + scalar * generator
def tweak_public_key(point_bytes: bytes, scalar_bytes: bytes):

    assert len(point_bytes) == 33
    assert len(scalar_bytes) == 32

    curve = ecdsa.SECP256k1
    point = ecdsa.VerifyingKey.from_string(point_bytes, curve).pubkey.point
    scalar = int.from_bytes(scalar_bytes, byteorder="big")

    result = point + scalar * curve.generator
    result_bytes = ecdsa.VerifyingKey.from_public_point(result, curve).to_string(
        "compressed"
    )

    return result_bytes
