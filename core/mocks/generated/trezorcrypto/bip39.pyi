from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def complete_word(prefix: str) -> Optional[str]:
    """
    Return the first word from the wordlist starting with prefix.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def word_completion_mask(prefix: str) -> int:
    """
    Return possible 1-letter suffixes for given word prefix.
    Result is a bitmask, with 'a' on the lowest bit, 'b' on the second
    lowest, etc.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def generate(strength: int) -> str:
    """
    Generate a mnemonic of given strength (128, 160, 192, 224 and 256 bits).
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def from_data(data: bytes) -> str:
    """
    Generate a mnemonic from given data (of 16, 20, 24, 28 and 32 bytes).
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def check(mnemonic: str) -> bool:
    """
    Check whether given mnemonic is valid.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def seed(
    mnemonic: str,
    passphrase: str,
    callback: Callable[[int, int], None] = None,
) -> bytes:
    """
    Generate seed from mnemonic and passphrase.
    """
