from typing import *
from buffer_types import *
from trezorcrypto.bip32 import HDNode
from trezorcrypto import secbytes


# upymod/modtrezorcrypto/modtrezorcrypto-cardano.h
def derive_icarus(
    binary_mnemonic: bytes | None,
    passphrase: str,
    trezor_derivation: bool,
    callback: Callable[[int, int], None] | None = None,
) -> secbytes:
    """Derive a sealed Cardano master secret; None reads protected
    storage."""


# upymod/modtrezorcrypto/modtrezorcrypto-cardano.h
def from_secret(secret: AnyBytes | secbytes) -> HDNode:
    """Create a protected Cardano HD node from a master secret."""


# upymod/modtrezorcrypto/modtrezorcrypto-cardano.h
def from_seed_slip23(seed: AnyBytes | secbytes) -> HDNode:
    """Create a protected Cardano node via SLIP-23."""


# upymod/modtrezorcrypto/modtrezorcrypto-cardano.h
def from_seed_ledger(seed: AnyBytes | secbytes) -> HDNode:
    """Create a protected Cardano node via Ledger derivation."""
