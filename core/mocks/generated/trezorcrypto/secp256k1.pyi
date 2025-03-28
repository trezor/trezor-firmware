from typing import *


# upymod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def generate_secret() -> bytes:
    """
    Generate secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def publickey(secret_key: bytes, compressed: bool = True) -> bytes:
    """
    Computes public key from secret key.
    """
CANONICAL_SIG_ETHEREUM: int = 1
CANONICAL_SIG_EOS: int = 2


# upymod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def sign_recoverable(
    secret_key: bytes,
    digest: bytes,
    canonical: int | None = None,
) -> bytes:
    """
    Uses secret key to produce the signature of the digest.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def anti_exfil_commit_nonce(
    secret_key: bytes,
    digest: bytes,
    entropy_commitment: bytes,
) -> bytes:
    """
    Commits to the signature nonce using the entropy from host. This funcion
    is a part of the anti-exfil protocol.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def anti_exfil_sign(
    secret_key: bytes,
    digest: bytes,
    entropy: bytes,
) -> bytes:
    """
    Signs the digest with the secret key using the entropy from host. This
    funcion is a part of the anti-exfil protocol.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
    """
    Uses public key to verify the signature of the digest.
    Returns True on success.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def verify_recover(signature: bytes, digest: bytes, compressed: bool = True)
-> bytes:
    """
    Uses signature of the digest to verify the digest and recover the public
    key. Returns public key on success, None if the signature is invalid.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def multiply(secret_key: bytes, public_key: bytes) -> bytes:
    """
    Multiplies point defined by public_key with scalar defined by
    secret_key. Useful for ECDH.
    """
