from typing import *
def generate(strength: int) -> str:
    """
    Generate a mnemonic of given strength (128, 160, 192, 224 and 256 bits).
    """
def from_data(data: bytes) -> str:
    """
    Generate a mnemonic from given data (of 16, 20, 24, 28 and 32 bytes).
    """
def check(mnemonic: str) -> bool:
    """
    Check whether given mnemonic is valid.
    """
def seed(
    mnemonic: str,
    passphrase: str,
    callback: Callable[[int, int], None] | None = None,
) -> bytes:
    """
    Generate seed from mnemonic and passphrase.
    """
