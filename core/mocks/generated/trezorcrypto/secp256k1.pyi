from typing import *
def generate_secret() -> bytes:
    """
    Generate secret key.
    """
def publickey(secret_key: bytes, compressed: bool = True) -> bytes:
    """
    Computes public key from secret key.
    """
CANONICAL_SIG_ETHEREUM: int = 1
CANONICAL_SIG_EOS: int = 2
def sign(
    secret_key: bytes,
    digest: bytes,
    compressed: bool = True,
    canonical: int | None = None,
) -> bytes:
    """
    Uses secret key to produce the signature of the digest.
    """
def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
    """
    Uses public key to verify the signature of the digest.
    Returns True on success.
    """
def verify_recover(signature: bytes, digest: bytes) -> bytes:
    """
    Uses signature of the digest to verify the digest and recover the public
    key. Returns public key on success, None if the signature is invalid.
    """
def multiply(secret_key: bytes, public_key: bytes) -> bytes:
    """
    Multiplies point defined by public_key with scalar defined by
    secret_key. Useful for ECDH.
    """
