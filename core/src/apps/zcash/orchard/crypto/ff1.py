"""
Slightly optimized implementation of FF1 algorithm
specified by Morris Dworkin in:

NIST Special Publication 800-38G
Recommendation for Block Cipher Modes of Operation: Methods for Format-Preserving Encryption
<http://dx.doi.org/10.6028/NIST.SP.800-38G>

Input message length is fixed to 88 bits.
Radix is fixed to 2.
"""


from typing import TYPE_CHECKING

from trezor.crypto import aes

from .utils import chain, lebs2ip, take

if TYPE_CHECKING:
    from typing import Iterable

    pass  # ff1.i


# big-endian bits to integer
def bebs2ip(bits: Iterable[int]) -> int:
    acc = 0
    for bit in bits:
        acc <<= 1
        acc += bit
    return acc


# integer to big endian bits
def i2bebsp(l: int, x: int) -> Iterable[int]:
    assert 0 <= x < (1 << l)
    for i in range(l):
        yield (x >> (l - 1 - i)) & 1
    return


def ff1_aes256_encrypt(key: bytes, tweak: bytes, x: Iterable[int]) -> Iterable[int]:
    n = 88  # n = len(x)
    t = len(tweak)
    assert t <= 255
    u, v = 44, 44  # u = n//2; v = n-u
    A = bebs2ip(take(u, x))
    B = bebs2ip(take(v, x))
    radix = 2
    b = 6  # b = cldiv(v, 8)
    d = 12  # d = 4*cldiv(b, 4) + 4
    P = bytes([1, 2, 1, 0, 0, radix, 10, u % 256, 0, 0, 0, n, 0, 0, 0, t])
    for i in range(10):
        Q = tweak + b"\x00" * ((-t - b - 1) % 16) + bytes([i]) + B.to_bytes(b, "big")
        y = int.from_bytes(aes_cbcmac(key, P + Q)[:d], "big")
        C = (A + y) & 0x0000_0FFF_FFFF_FFFF  # 44-bit mask
        A, B = B, C

    return chain(i2bebsp(u, A), i2bebsp(v, B))


def aes_cbcmac(key: bytes, input: bytes) -> bytes:
    cipher = aes(aes.CBC, key, b"\x00" * 16)
    mac = cipher.encrypt(input)[-16:]
    del cipher
    return mac


def to_radix(message: bytes) -> Iterable[int]:
    for n in message:
        for _ in range(8):
            yield n & 1
            n >>= 1
    return


def from_radix(bits: Iterable[int]) -> bytes:
    data = []
    for _ in range(11):
        byte = take(8, bits)
        data.append(lebs2ip(byte))
    return bytes(data)


# https://zips.z.cash/protocol/protocol.pdf#concreteprps
def encrypt_diversifier_index(dk: bytes, index: int) -> bytes:
    index_bits = to_radix(index.to_bytes(11, "little"))
    diversifier_bits = ff1_aes256_encrypt(dk, b"", index_bits)
    return from_radix(diversifier_bits)
