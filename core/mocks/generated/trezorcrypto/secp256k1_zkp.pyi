from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1_zkp.h
class RangeProofConfig:
    """
    Range proof configuration.
    """

    def __init__(self, min_value: int, exponent: int, bits: int):
        """
        Initialize range proof configuration.
        """


# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1_zkp.h
class Context:
    """
    Owns a secp256k1 context.
    Can be allocated once and re-used between subsequent operations.
    """

    def __init__(self) -> None:
        """
        Allocate and initialize secp256k1_zkp context object.
        """

    def __enter__(self) -> None:
        """
        Allocate and initialize secp256k1_context memory.
        """

    def __exit__(self, *args: Any) -> None:
        """
        Erase and free secp256k1_context memory.
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

    def blind_generator(self, asset: bytes, blinder: bytes) -> bytes:
        '''
        Generate blinded generator for the specified confidential asset.
        '''

    def pedersen_commit(self, value: int, blinder: bytes, gen: bytes) -> bytes:
        '''
        Commit to specified integer value, using given 32-byte blinding factor.
        '''

    def balance_blinds(self, values: Tuple[int], value_blinds: bytearray,
                       asset_blinds: bytes, num_of_inputs: int) -> None:
        '''
        Balance value blinds (by updating value_blinds in-place).
        '''

    def verify_balance(self, commits: Tuple[bytes], n_inputs: int) -> None:
        '''
        Verify that Pedersen commitments are balanced.
        '''

    def rangeproof_sign(self, config: RangeProofConfig, value: int,
                        commit: bytes, blind: bytes, nonce: bytes,
                        message: bytes, extra_commit: bytes,
                        gen: bytes) -> memoryview:
        '''
        Return a range proof for specified value (as a memoryview of the
        underlying rangeproof_buffer).
        '''
