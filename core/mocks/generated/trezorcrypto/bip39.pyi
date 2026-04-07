from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-bip39.h
def from_data(data: AnyBytes) -> str:
    """
    Generate a mnemonic from given data (of 16, 20, 24, 28 and 32 bytes).
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip39.h
def check(mnemonic: str) -> bool:
    """
    Check whether given mnemonic is valid.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip39.h
def seed(
    mnemonic: str,
    passphrase: str,
    callback: Callable[[int, int], None] | None = None,
) -> bytes:
    """
    Generate seed from mnemonic and passphrase.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip39.h
def mnemonic_to_bits(mnemonic: str) -> bytes:
    """
    Convert the mnemonic to its binary representation (including checksum).
    """
