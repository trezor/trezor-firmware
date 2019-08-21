from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1_zkp.h
class Context:
    """
    Owns a secp256k1 context.
    Can be allocated once and re-used between subsequent operations.
    """

    def __init__(self) -> None:
        """
        Allocate and initialize secp256k1_context.
        """

    def __del__(self) -> None:
        """
        Destructor.
        """

    def size(self) -> int:
        """
        Return the size in bytes of the internal secp256k1_ctx_buf buffer.
        """

    def generate_secret(self) -> bytes:
        """
        Generate secret key.
        """

    def publickey(self, secret_key: bytes, compressed: bool = True) -> bytes:
        """
        Computes public key from secret key.
        """

    def sign(
        self, secret_key: bytes, digest: bytes, compressed: bool = True
    ) -> bytes:
        """
        Uses secret key to produce the signature of the digest.
        """

    def verify(
        self, public_key: bytes, signature: bytes, digest: bytes
    ) -> bool:
        """
        Uses public key to verify the signature of the digest.
        Returns True on success.
        """

    def verify_recover(self, signature: bytes, digest: bytes) -> bytes:
        """
        Uses signature of the digest to verify the digest and recover the public
        key. Returns public key on success, None if the signature is invalid.
        """

    def multiply(self, secret_key: bytes, public_key: bytes) -> bytes:
        """
        Multiplies point defined by public_key with scalar defined by
        secret_key. Useful for ECDH.
        """
