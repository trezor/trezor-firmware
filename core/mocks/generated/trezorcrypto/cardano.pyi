from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-cardano.h
def derive_icarus_trezor(
    mnemonic: str,
    passphrase: str,
    callback: Callable[[int, int], None] | None = None,
) -> bytes:
    """
    Derives a Cardano master secret from a mnemonic and passphrase using the
    Icarus-Trezor derivation scheme. This differs from the Icarus scheme by
    including checksum if the mnemonic is 24 words.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-cardano.h
def from_secret(secret: bytes) -> HDNode:
    """
    Creates a Cardano HD node from a master secret.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-cardano.h
def from_seed_slip23(seed: bytes) -> HDNode:
   """
   Creates a Cardano HD node from a seed via SLIP-23 derivation.
   """
