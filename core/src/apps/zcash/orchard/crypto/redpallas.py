# https://zips.z.cash/protocol/protocol.pdf#concretereddsa

from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake2b
from trezor.crypto.pallas import to_scalar

from .generators import SPENDING_KEY_BASE
from .utils import xor

if TYPE_CHECKING:
    from trezor.crypto.pallas import Scalar
    from ..random import ActionShieldingRng

    pass


def randomize(sk: Scalar, randomizer: Scalar) -> Scalar:
    return sk + randomizer


def H_star(x: bytes) -> Scalar:
    digest = blake2b(personal=b"Zcash_RedPallasH", data=x).digest()
    return to_scalar(digest)


def sign_spend_auth(sk: Scalar, message: bytes, rng: ActionShieldingRng) -> bytes:
    # According to the Redpallas specification, `T` should be uniformly random
    # sequence of 32 bytes. Since Trezor output must be deterministic (to prevent
    # secret leakage caused by mallicious hw randomness generator), we set
    T = xor(rng.spend_auth_T(), sk.to_bytes())
    # - `rng.spend_auth_T()` randomizes the signature
    # - xoring with bytes of `sk` makes `T` unpredictable for outside

    vk: bytes = (sk * SPENDING_KEY_BASE).to_bytes()
    r: Scalar = H_star(T + vk + message)
    R: bytes = (r * SPENDING_KEY_BASE).to_bytes()
    e: Scalar = H_star(R + vk + message)
    S: bytes = (r + e * sk).to_bytes()
    return R + S
