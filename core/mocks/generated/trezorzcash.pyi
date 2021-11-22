from typing import *


# extmod/rustmods/modtrezorzcash.c
def get_orchard_fvk(sk: bytes) -> bytes:
"""Returns a raw Orchard Full Viewing Key."""


# extmod/rustmods/modtrezorzcash.c
def get_orchard_ivk(sk: bytes) -> bytes:
"""Returns a raw Orchard Incoming Viewing Key."""


# extmod/rustmods/modtrezorzcash.c
def get_orchard_address(
    sk: bytes
    diversifier_index: int
) -> bytes:
"""Returns a raw Orchard address."""


# extmod/rustmods/modtrezorzcash.c
def f4jumble(message: bytearray) -> None:
    """Mutates a message by F4Jumble permutation."""


# extmod/rustmods/modtrezorzcash.c
def f4jumble_inv(message: bytearray) -> None:
    """Mutates a message by F4Jumble inverse permutation."""
