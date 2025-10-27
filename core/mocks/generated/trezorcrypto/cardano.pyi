from typing import *
from buffer_types import *
from trezorcrypto.bip32 import HDNode


# upymod/modtrezorcrypto/modtrezorcrypto-cardano.h
def derive_icarus(
    binary_mnemonic: bytes,
    passphrase: str,
    trezor_derivation: bool,
    callback: Callable[[int, int], None] | None = None,
) -> bytes:
    """
    Derives a Cardano master secret from a mnemonic represented in bits
    (including checksum) and a passphrase using the Icarus derivation
    scheme. If `trezor_derivation` is True, the Icarus-Trezor variant is
    used (see CIP-3).
    """


# upymod/modtrezorcrypto/modtrezorcrypto-cardano.h
def from_secret(secret: AnyBytes) -> HDNode:
    """
    Creates a Cardano HD node from a master secret.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-cardano.h
def from_seed_slip23(seed: AnyBytes) -> HDNode:
   """
   Creates a Cardano HD node from a seed via SLIP-23 derivation.
   """


# upymod/modtrezorcrypto/modtrezorcrypto-cardano.h
def from_seed_ledger(seed: AnyBytes) -> HDNode:
    """
    Creates a Cardano HD node from a seed via Ledger derivation.
    """
