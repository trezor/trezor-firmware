"""
Implementation of Sinsemilla hash function.
see: https://zips.z.cash/protocol/protocol.pdf#concretesinsemillahash
"""

from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto.pallas import group_hash
from trezor.utils import ensure

from .utils import i2leosp, lebs2ip

if TYPE_CHECKING:
    from trezor.crypto.pallas import Point

    pass  # sinsemilla.i


K = const(10)


def iadd(a: Point, b: Point) -> Point:
    """Incomplete addition."""
    ensure(not a.is_identity())
    ensure(not b.is_identity())
    ensure(a != b)
    ensure(a != -b)
    return a + b


class Sinsemilla:
    def __init__(self, acc):
        self.buffer = []
        self.acc = acc

    @staticmethod
    def personalized_by(personal: bytes):
        Q = group_hash("z.cash:SinsemillaQ", personal)
        return Sinsemilla(Q)

    def update(self, bits):
        for bit in bits:
            self.buffer.append(bit)
            if len(self.buffer) == K:
                self.digest_buffer()

    def digest_buffer(self):
        index = lebs2ip(self.buffer)
        S = group_hash("z.cash:SinsemillaS", i2leosp(32, index))
        acc = self.acc
        self.acc = iadd(iadd(acc, S), acc)
        self.buffer.clear()

    def finalize(self):
        if len(self.buffer) > 0:
            self.buffer.extend([0] * (K - len(self.buffer)))  # padding
            self.digest_buffer()
        return self.acc
