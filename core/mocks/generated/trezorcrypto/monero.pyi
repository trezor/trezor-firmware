from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
class Ge25519:
    """
    EC point on ED25519
    """
    def __init__(self, x: Optional[Union[Ge25519, bytes]] = None):
        """
        Constructor
        """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
class Sc25519:
    """
    EC scalar on SC25519
    """
    def __init__(self, x: Optional[Union[Sc25519, bytes, int]] = None):
        """
        Constructor
        """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
class Hasher:
    """
    XMR hasher
    """
    def __init__(self, x: Optional[bytes] = None):
        """
        Constructor
        """
    def update(self, buffer: bytes) -> None:
        """
        Update hasher
        """
    def digest(self) -> bytes:
        """
        Computes digest
        """
    def copy(self) -> Hasher:
        """
        Creates copy of the hasher, preserving the state
        """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def init256_modm(
    dst: Optional[Sc25519], val: Union[int, bytes, Sc25519]
) -> Sc25519:
    """
    Initializes Sc25519 scalar
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def check256_modm(val: Sc25519) -> None:
    """
    Throws exception if scalar is invalid
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def iszero256_modm(val: Sc25519) -> bool:
    """
    Returns False if the scalar is zero
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def eq256_modm(a: Sc25519, b: Sc25519) -> int:
    """
    Compares scalars, returns 1 on the same value
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def get256_modm(a: Sc25519) -> int:
    """
    Extracts 64bit integer from the scalar. Raises exception if scalar is
    bigger than 2^64
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def add256_modm(r: Optional[Sc25519], a: Sc25519, b: Sc25519) -> Sc25519:
    """
    Scalar addition
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def sub256_modm(r: Optional[Sc25519], a: Sc25519, b: Sc25519) -> Sc25519:
    """
    Scalar subtraction
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def mul256_modm(r: Optional[Sc25519], a: Sc25519, b: Sc25519) -> Sc25519:
    """
    Scalar multiplication
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def mulsub256_modm(
    r: Optional[Sc25519], a: Sc25519, b: Sc25519, c: Sc25519
) -> Sc25519:
    """
    c - a*b
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def muladd256_modm(
    r: Optional[Sc25519], a: Sc25519, b: Sc25519, c: Sc25519
) -> Sc25519:
    """
    c + a*b
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def inv256_modm(r: Optional[Sc25519], a: Sc25519) -> Sc25519:
    """
    Scalar modular inversion
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def pack256_modm(
    r: Optional[bytes], a: Sc25519, offset: Optional[int] = 0
) -> bytes:
    """
    Scalar compression
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def unpack256_modm(
    r: Optional[Sc25519], a: bytes, offset: int = 0
) -> Sc25519:
    """
    Scalar decompression
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def unpack256_modm_noreduce(
    r: Optional[Sc25519], a: bytes, offset: int = 0
) -> Sc25519:
    """
    Scalar decompression, raw, without modular reduction
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_set_neutral(r: Optional[Ge25519]) -> Ge25519:
    """
    Sets neutral point
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_set_xmr_h(r: Optional[Ge25519]) -> Ge25519:
    """
    Sets H point
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_check(r: Ge25519) -> None:
    """
    Checks point, throws if not on curve
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_eq(a: Ge25519, b: Ge25519) -> bool:
    """
    Compares EC points
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_add(r: Optional[Ge25519], a: Ge25519, b: Ge25519) -> Ge25519:
    """
    Adds EC points
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_sub(r: Optional[Ge25519], a: Ge25519, b: Ge25519) -> Ge25519:
    """
    Subtracts EC points
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_double(r: Optional[Ge25519], p: Ge25519) -> Ge25519:
    """
    EC point doubling
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_mul8(r: Optional[Ge25519], p: Ge25519) -> Ge25519:
    """
    EC point * 8
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_double_scalarmult_vartime(
    r: Optional[Ge25519], p1: Ge25519, s1: Sc25519, s2: Sc25519
) -> Ge25519:
    """
    s1 * G + s2 * p1
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_double_scalarmult_vartime2(
    r: Optional[Ge25519],
    p1: Ge25519,
    s1: Sc25519,
    p2: Ge25519,
    s2: Sc25519,
) -> Ge25519:
    """
    s1 * p1 + s2 * p2
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_scalarmult_base(
    r: Optional[Ge25519], s: Union[Sc25519, int]
) -> Ge25519:
    """
    s * G
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_scalarmult(
    r: Optional[Ge25519], p: Ge25519, s: Union[Sc25519, int]
) -> Ge25519:
    """
    s * p
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_pack(r: bytes, p: Ge25519, offset: int = 0) -> bytes:
    """
    Point compression
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_unpack_vartime(
    r: Optional[Ge25519], buff: bytes, offset: int = 0
) -> Ge25519:
    """
    Point decompression
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def base58_addr_encode_check(tag: int, buff: bytes) -> bytes:
    """
    Monero block base 58 encoding
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def base58_addr_decode_check(buff: bytes) -> Tuple[bytes, int]:
    """
    Monero block base 58 decoding, returning (decoded, tag) or raising on
    error.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_random_scalar(r: Optional[Sc25519] = None) -> Sc25519:
    """
    Generates a random scalar
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_fast_hash(r: Optional[bytes], buff: bytes, length: int, offset: int) -> bytes:
    """
    XMR fast hash
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_hash_to_ec(r: Optional[Ge25519], buff: bytes, length: int, offset:
int) -> Ge25519:
    """
    XMR hashing to EC point
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_hash_to_scalar(r: Optional[Sc25519], buff: bytes, length: int,
offset: int) -> Sc25519:
    """
    XMR hashing to EC scalar
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_derivation_to_scalar(
    r: Optional[Sc25519], p: Ge25519, output_index: int
) -> Sc25519:
    """
    H_s(derivation || varint(output_index))
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_generate_key_derivation(
    r: Optional[Ge25519], A: Ge25519, b: Sc25519
) -> Ge25519:
    """
    8*(key2*key1)
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_derive_private_key(
    r: Optional[Sc25519], deriv: Ge25519, idx: int, base: Sc25519
) -> Sc25519:
    """
    base + H_s(derivation || varint(output_index))
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_derive_public_key(
    r: Optional[Ge25519], deriv: Ge25519, idx: int, base: Ge25519
) -> Ge25519:
    """
    H_s(derivation || varint(output_index))G + base
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_add_keys2(
    r: Optional[Ge25519], a: Sc25519, b: Sc25519, B: Ge25519
) -> Ge25519:
    """
    aG + bB, G is basepoint
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_add_keys2_vartime(
    r: Optional[Ge25519], a: Sc25519, b: Sc25519, B: Ge25519
) -> Ge25519:
    """
    aG + bB, G is basepoint
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_add_keys3(
    r: Optional[Ge25519], a: Sc25519, A: Ge25519, b: Sc25519, B: Ge25519
) -> Ge25519:
    """
    aA + bB
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_add_keys3_vartime(
    r: Optional[Ge25519], a: Sc25519, A: Ge25519, b: Sc25519, B: Ge25519
) -> Ge25519:
    """
    aA + bB
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_get_subaddress_secret_key(
    r: Optional[Sc25519], major: int, minor: int, m: Sc25519
) -> Sc25519:
    """
    Hs(SubAddr || a || index_major || index_minor)
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_gen_c(r: Optional[Ge25519], a: Sc25519, amount: int) -> Ge25519:
    """
    aG + amount * H
    """


# extmod/modtrezorcrypto/modtrezorcrypto-monero.h
def ct_equals(a: bytes, b: bytes) -> bool:
    """
    Constant time buffer comparison
    """
