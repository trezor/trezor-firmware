from typing import *


# upymod/modtrezorcrypto/modtrezorcrypto-tropic.h
class TropicError(Exception):
    """Error returned by the Tropic Square chip."""

    def ping(message: str) -> str:
        """
        Test the session by pinging the chip.
        """

    def get_certificate() -> bytes:
        """
        Return the chip's certificate.
        """

    def key_generate(
        key_index: int,
    ) -> None:
        """
        Generate ECC key in the device's ECC key slot.
        """

    def sign(
        key_index: int,
        digest: bytes,
    ) -> bytes:
        """
        Uses the private key at key_index to produce a signature of the digest.
        """
