from typing import *


# extmod/rustmods/modtrezororchardlib.c
def get_orchard_fvk(sk: bytes) -> bytes:
"""Returns a raw Orchard Full Viewing Key."""


# extmod/rustmods/modtrezororchardlib.c
def get_orchard_ivk(sk: bytes) -> bytes:
"""Returns a raw Orchard Incoming Viewing Key."""


# extmod/rustmods/modtrezororchardlib.c
def get_orchard_address(
    sk: bytes
    diversifier_index: int
) -> bytes:
"""Returns a raw Orchard address."""


# extmod/rustmods/modtrezororchardlib.c
def f4jumble(message: bytearray) -> None:
    """Mutates a message by F4Jumble permutation."""


# extmod/rustmods/modtrezororchardlib.c
def f4jumble_inv(message: bytearray) -> None:
    """Mutates a message by F4Jumble inverse permutation."""


# extmod/rustmods/modtrezororchardlib.c
def shield(
    action_info,
    rng_config,
):
"""Returns an action descripription as serialized in the ledger
   and attached alpha randomizer."""


# extmod/rustmods/modtrezororchardlib.c
def sign(
    sk: bytes,
    alpha: bytes,
    sighash: bytes,
):
"""reddsa spend signature of over pallas
 
# Args:
    `sk` - spending key
    `alpha` - randomizer (pallas scalar)
    `sighash` - signed data
"""
