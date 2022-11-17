from typing import TYPE_CHECKING

from trezor.crypto.pallas import Point, group_hash

if TYPE_CHECKING:
    from trezor.crypto.pallas import Scalar


# https://zips.z.cash/protocol/protocol.pdf#concretediversifyhash
def diversify_hash(d: bytes) -> Point:
    P = group_hash("z.cash:Orchard-gd", d)
    if P.is_identity():
        P = group_hash("z.cash:Orchard-gd", b"")
    return P


class Address:
    def __init__(self, d: bytes, pk_d: Point) -> None:
        assert len(d) == 11
        self.d = d
        self.pk_d = pk_d

    @staticmethod
    def from_bytes(data: bytes) -> "Address":
        assert len(data) == 43
        return Address(data[:11], Point(data[11:]))

    @staticmethod
    def from_ivk(d: bytes, ivk: Scalar):
        g_d = diversify_hash(d)
        pk_d = ivk * g_d
        return Address(d, pk_d)

    # https://zips.z.cash/protocol/nu5.pdf#orchardpaymentaddrencoding
    def to_bytes(self) -> bytes:
        return self.d + self.pk_d.to_bytes()

    def g_d(self) -> Point:
        return diversify_hash(self.d)
