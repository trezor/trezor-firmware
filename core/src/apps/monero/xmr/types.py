from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.crypto import monero as tcry

    Ge25519 = tcry.ge25519
    Sc25519 = tcry.bignum256modm
