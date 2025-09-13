from typing import *


# upymod/modtrezorcrypto/modtrezorcrypto-tropic.h
class TropicError(Exception):
    """Error returned by the Tropic Square chip."""


# upymod/modtrezorcrypto/modtrezorcrypto-tropic.h
def ping(message: str) -> str:
    """
    Test the session by pinging the chip.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-tropic.h
def key_generate(
    key_index: int,
) -> None:
    """
    Generate ECC key in the device's ECC key slot.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-tropic.h
def sign(
    key_index: int,
    digest: bytes,
) -> bytes:
    """
    Uses the private key at key_index to produce a signature of the digest.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-tropic.h
def get_user_data(index: int) -> bytes:
    """
    Return the user data stored at the given index.
    """
DEVICE_CERT_INDEX: int
DEVICE_KEY_SLOT: int
FIDO_CERT_INDEX: int
FIDO_KEY_SLOT: int
