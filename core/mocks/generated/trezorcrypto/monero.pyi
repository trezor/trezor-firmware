from typing import *


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
class Point:
    """
    EC point on ED25519
    """
    def __init__(self, x: Point | bytes | None = None):
        """
        Constructor
        """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
class Scalar:
    """
    EC scalar on SC25519
    """
    def __init__(self, x: Scalar | bytes | int | None = None):
        """
        Constructor
        """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
class Hasher:
    """
    XMR hasher
    """
    def __init__(self, x: bytes | None = None):
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


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_copy(
    dst: Scalar | None, val: int | bytes | Scalar
) -> Scalar:
    """
    Initializes a scalar
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_check(val: Scalar) -> None:
    """
    Throws exception if scalar is invalid
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_iszero(val: Scalar) -> bool:
    """
    Returns False if the scalar is zero
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_eq(a: Scalar, b: Scalar) -> int:
    """
    Compares scalars, returns 1 on the same value
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_add_into(r: Scalar | None, a: Scalar, b: Scalar) -> Scalar:
    """
    Scalar addition
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_sub_into(r: Scalar | None, a: Scalar, b: Scalar) -> Scalar:
    """
    Scalar subtraction
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_mul_into(r: Scalar | None, a: Scalar, b: Scalar) -> Scalar:
    """
    Scalar multiplication
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_mulsub_into(
    r: Scalar | None, a: Scalar, b: Scalar, c: Scalar
) -> Scalar:
    """
    c - a*b
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_muladd_into(
    r: Scalar | None, a: Scalar, b: Scalar, c: Scalar
) -> Scalar:
    """
    c + a*b
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def sc_inv_into(r: Scalar | None, a: Scalar) -> Scalar:
    """
    Scalar modular inversion
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def encodeint_into(
    r: bytes | None, a: Scalar, offset: int | None = 0
) -> bytes:
    """
    Scalar compression
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def decodeint_into(
    r: Scalar | None, a: bytes, offset: int = 0
) -> Scalar:
    """
    Scalar decompression
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def decodeint_into_noreduce(
    r: Scalar | None, a: bytes, offset: int = 0
) -> Scalar:
    """
    Scalar decompression, raw, without modular reduction
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def identity_into(r: Point | None = None) -> Point:
    """
    Sets neutral point
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_H(r: Point | None = None) -> Point:
    """
    Sets H point
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_check(r: Point) -> None:
    """
    Checks point, throws if not on curve
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def point_eq(a: Point, b: Point) -> bool:
    """
    Compares EC points
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def point_add_into(r: Point | None, a: Point, b: Point) -> Point:
    """
    Adds EC points
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def point_sub_into(r: Point | None, a: Point, b: Point) -> Point:
    """
    Subtracts EC points
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_mul8(r: Point | None, p: Point) -> Point:
    """
    EC point * 8
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def ge25519_double_scalarmult_vartime_into(
    r: Point | None, p1: Point, s1: Scalar, s2: Scalar
) -> Point:
    """
    s1 * G + s2 * p1
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def scalarmult_base_into(
    r: Point | None, s: Scalar | int
) -> Point:
    """
    s * G
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def scalarmult_into(
    r: Point | None, p: Point, s: Scalar | int
) -> Point:
    """
    s * p
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def encodepoint_into(r: bytes | None, p: Point, offset: int = 0) -> bytes:
    """
    Point compression
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def decodepoint_into(
    r: Point | None, buff: bytes, offset: int = 0
) -> Point:
    """
    Point decompression
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_base58_addr_encode_check(tag: int, buff: bytes) -> str:
    """
    Monero block base 58 encoding
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_base58_addr_decode_check(buff: bytes) -> tuple[bytes, int]:
    """
    Monero block base 58 decoding, returning (decoded, tag) or raising on
    error.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def random_scalar(r: Scalar | None = None) -> Scalar:
    """
    Generates a random scalar
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def fast_hash_into(
   r: bytes | None,
   buff: bytes,
   length: int | None = None,
   offset: int = 0,
) -> bytes:
    """
    XMR fast hash
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def hash_to_point_into(
    r: Point | None,
    buff: bytes,
    length: int | None = None,
    offset: int = 0,
) -> Point:
    """
    XMR hashing to EC point
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def hash_to_scalar_into(
   r: Scalar | None,
   buff: bytes,
   length: int | None = None,
   offset: int = 0,
) -> Scalar:
    """
    XMR hashing to EC scalar
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_derivation_to_scalar(
    r: Scalar | None, p: Point, output_index: int
) -> Scalar:
    """
    H_s(derivation || varint(output_index))
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_generate_key_derivation(
    r: Point | None, A: Point, b: Scalar
) -> Point:
    """
    8*(key2*key1)
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_derive_private_key(
    r: Scalar | None, deriv: Point, idx: int, base: Scalar
) -> Scalar:
    """
    base + H_s(derivation || varint(output_index))
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_derive_public_key(
    r: Point | None, deriv: Point, idx: int, base: Point
) -> Point:
    """
    H_s(derivation || varint(output_index))G + base
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def add_keys2_into(
    r: Point | None, a: Scalar, b: Scalar, B: Point
) -> Point:
    """
    aG + bB, G is basepoint
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def add_keys3_into(
    r: Point | None, a: Scalar, A: Point, b: Scalar, B: Point
) -> Point:
    """
    aA + bB
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def xmr_get_subaddress_secret_key(
    r: Scalar | None, major: int, minor: int, m: Scalar
) -> Scalar:
    """
    Hs(SubAddr || a || index_major || index_minor)
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def gen_commitment_into(r: Point | None, a: Scalar, amount: int) -> Point:
    """
    aG + amount * H
    """


# upymod/modtrezorcrypto/modtrezorcrypto-monero.h
def ct_equals(a: bytes, b: bytes) -> bool:
    """
    Constant time buffer comparison
    """
BP_GI_PLUS_PRE: bytes
BP_HI_PLUS_PRE: bytes
