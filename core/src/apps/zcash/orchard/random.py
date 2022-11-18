from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake2b
from trezor.crypto.pallas import to_base, to_scalar
from trezor.utils import chunks

from .crypto.address import Address
from .crypto.keys import sk_to_ask

if TYPE_CHECKING:
    from typing import Any, Iterator
    from trezor.crypto.pallas import Scalar, Fp


class BundleShieldingRng:
    def __init__(self, seed: bytes) -> None:
        self.seed = seed

    def for_action(self, i: int) -> "ActionShieldingRng":
        h = blake2b(personal=b"ActionShieldSeed", outlen=32)
        h.update(self.seed)
        h.update(i.to_bytes(4, "little"))
        return ActionShieldingRng(h.digest())

    def shuffle_inputs(self, inputs: list[int | None]) -> None:
        rng = self._blake2b_ctr_mode_rng(personal=b"Inps_Permutation")
        _shuffle(inputs, rng)

    def shuffle_outputs(self, outputs: list[int | None]) -> None:
        rng = self._blake2b_ctr_mode_rng(personal=b"Outs_Permutation")
        _shuffle(outputs, rng)

    def _blake2b_ctr_mode_rng(self, personal: bytes) -> Iterator[int]:
        i = 0
        while True:
            h = blake2b(personal=personal, outlen=64)
            h.update(self.seed)
            h.update(i.to_bytes(4, "little"))
            digest = h.digest()
            for chunk in chunks(digest, 4):
                yield int.from_bytes(chunk, "little")
            i += 1


MAX = const(0xFFFF_FFFF)


def _sample_uniform(n: int, rng: Iterator[int]) -> int:
    """Samples unifomly an element of `range(n)`."""
    while True:
        wide = next(rng) * n
        high = wide >> 32
        low = wide & MAX
        if low <= MAX - n or low <= MAX - (MAX - n) % n:
            return high


def _shuffle(x: list[Any], rng: Iterator[int]) -> None:
    # Fisher-Yates shuffle
    for i in range(len(x) - 1, 0, -1):
        j = _sample_uniform(i + 1, rng)
        x[i], x[j] = x[j], x[i]


class ActionShieldingRng:
    def __init__(self, seed: bytes) -> None:
        self.seed = seed

    def random(self, dst: bytes, outlen: int = 64) -> bytes:
        h = blake2b(personal=b"ActionExpandSeed", outlen=outlen)
        h.update(self.seed)
        h.update(dst)
        return h.digest()

    def alpha(self) -> Scalar:
        return to_scalar(self.random(b"alpha"))

    def rcv(self) -> Scalar:
        return to_scalar(self.random(b"rcv"))

    def recipient(self) -> Address:
        d = self.random(b"dummy_d", 11)
        ivk = to_scalar(self.random(b"dummy_ivk"))
        return Address.from_ivk(d, ivk)

    def ock(self) -> bytes:
        return self.random(b"dummy_ock", 32)

    def op(self) -> bytes:
        return self.random(b"dummy_op", 64)

    def rseed_old(self) -> bytes:
        return self.random(b"dummy_rseed_old", 32)

    def rseed_new(self) -> bytes:
        return self.random(b"rseed_new", 32)

    def dummy_sk(self) -> bytes:
        return self.random(b"dummy_sk", 32)

    def dummy_ask(self) -> Scalar:
        return sk_to_ask(self.dummy_sk())

    def rho(self) -> Fp:
        return to_base(self.random(b"dummy_rho"))

    def spend_auth_T(self) -> bytes:
        return self.random(b"spend_auth_T", 32)
