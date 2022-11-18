from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake2b
from trezor.crypto.pallas import Fp, Scalar

if TYPE_CHECKING:
    from typing import TypeVar, Iterable, Iterator
    A = TypeVar("A")


def xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


# https://zips.z.cash/protocol/protocol.pdf#concreteprfs
def prf_expand(sk: bytes, t: bytes) -> bytes:
    digest = blake2b(personal=b"Zcash_ExpandSeed")
    digest.update(sk)
    digest.update(t)
    return digest.digest()


# ceil div (div rounded up)
def cldiv(n, divisor):
    return (n + (divisor - 1)) // divisor


# integer to little-endian bits
def i2lebsp(l: int, x: Fp | Scalar | int) -> Iterator[int]:
    if isinstance(x, Fp) or isinstance(x, Scalar):
        gen = leos2bsp(x.to_bytes())
        for _ in range(l):
            yield next(gen)
    elif isinstance(x, int):
        for i in range(l):
            yield (x >> i) & 1
    else:
        raise ValueError()


# integer to little-endian bytes
def i2leosp(l: int, x: int) -> bytes:
    return x.to_bytes(cldiv(l, 8), "little")


# little endian bits to interger
def lebs2ip(bits: Iterable[int]) -> int:
    acc = 0
    for i, bit in enumerate(bits):
        acc += bit << i
    return acc


# little-endian bytes to little-endian bits
def leos2bsp(buf: bytes) -> Iterator[int]:
    for byte in buf:
        for i in range(8):
            yield (byte >> i) & 1


def take(i: int, gen: Iterator[A] | list[A]) -> Iterator[A]:
    """Creates a new generator, which returns `i` elements
    of the original generator."""
    if isinstance(gen, list):
        gen = iter(gen)
    for _ in range(i):
        yield next(gen)


def chain(gen_a: Iterable[A], gen_b: Iterable[A]) -> Iterable[A]:
    """Chains two generators into one."""
    yield from gen_a
    yield from gen_b
