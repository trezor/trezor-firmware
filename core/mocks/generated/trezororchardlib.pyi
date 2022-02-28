from typing import *


# extmod/rustmods/modtrezororchardlib.c
def derive_full_viewing_key(spending_key: bytes, internal: bool) -> bytes:
"""Returns a raw Orchard Full Viewing Key."""


# extmod/rustmods/modtrezororchardlib.c
def derive_internal_full_viewing_key(full_viewing_key: bytes) -> bytes:
"""Returns a raw internal Orchard Full Viewing Key."""


# extmod/rustmods/modtrezororchardlib.c
def derive_incoming_viewing_key(full_viewing_key: bytes, internal: bool) -> bytes:
"""Returns a raw Orchard Incoming Viewing Key."""


# extmod/rustmods/modtrezororchardlib.c
def derive_outgoing_viewing_key(full_viewing_key: bytes, internal: bool) -> bytes:
"""Returns a raw Orchard Outgoing Viewing Key."""


# extmod/rustmods/modtrezororchardlib.c
def derive_address(
    full_viewing_key: bytes,
    diversifier_index: int,
    internal: bool,
) -> bytes:
"""Returns a raw Orchard address."""


# extmod/rustmods/modtrezororchardlib.c
def f4jumble(message: bytearray) -> None:
    """Mutates a message by F4Jumble permutation."""


# extmod/rustmods/modtrezororchardlib.c
def f4jumble_inv(message: bytearray) -> None:
    """Mutates a message by F4Jumble inverse permutation."""


# extmod/rustmods/modtrezororchardlib.c
def shuffle(
    list,
    rng_config,
):
"""Shuffles a list."""


# extmod/rustmods/modtrezororchardlib.c
def shield(
    action_info,
    rng_config,
):
"""Returns an action descripription as serialized in the ledger
   and attached alpha randomizer."""


# extmod/rustmods/modtrezororchardlib.c
def sign(
    spending_key: bytes,
    alpha: bytes,
    sighash: bytes,
):
"""reddsa spend signature of over pallas
 
# Args:
    `spending_key` - spending key
    `alpha` - randomizer (pallas scalar)
    `sighash` - message digest
"""
