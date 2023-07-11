from typing import *
class Point:
        """
        EC point on ED25519
        """

        def __init__(self, x: Point | bytes | None = None):
            """
            Constructor
            """
class Scalar:
        """
        EC scalar on SC25519
        """

        def __init__(self, x: Scalar | bytes | int | None = None):
            """
            Constructor
            """


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


def sc_copy(
    dst: Scalar | None, val: int | bytes | Scalar
) -> Scalar:
    """
    Initializes a scalar
    """
def sc_check(val: Scalar) -> None:
    """
    Throws exception if scalar is invalid
    """
def sc_iszero(val: Scalar) -> bool:
    """
    Returns False if the scalar is zero
    """
def sc_eq(a: Scalar, b: Scalar) -> int:
    """
    Compares scalars, returns 1 on the same value
    """
def sc_add_into(r: Scalar | None, a: Scalar, b: Scalar) -> Scalar:
    """
    Scalar addition
    """
def sc_sub_into(r: Scalar | None, a: Scalar, b: Scalar) -> Scalar:
    """
    Scalar subtraction
    """
def sc_mul_into(r: Scalar | None, a: Scalar, b: Scalar) -> Scalar:
    """
    Scalar multiplication
    """
def sc_mulsub_into(
    r: Scalar | None, a: Scalar, b: Scalar, c: Scalar
) -> Scalar:
    """
    c - a*b
    """
def sc_muladd_into(
    r: Scalar | None, a: Scalar, b: Scalar, c: Scalar
) -> Scalar:
    """
    c + a*b
    """
def sc_inv_into(r: Scalar | None, a: Scalar) -> Scalar:
    """
    Scalar modular inversion
    """
def encodeint_into(
    r: bytes | None, a: Scalar, offset: int | None = 0
) -> bytes:
    """
    Scalar compression
    """
def decodeint_into(
    r: Scalar | None, a: bytes, offset: int = 0
) -> Scalar:
    """
    Scalar decompression
    """
def decodeint_into_noreduce(
    r: Scalar | None, a: bytes, offset: int = 0
) -> Scalar:
    """
    Scalar decompression, raw, without modular reduction
    """
def identity_into(r: Point | None = None) -> Point:
    """
    Sets neutral point
    """
def xmr_H(r: Point | None = None) -> Point:
    """
    Sets H point
    """
def ge25519_check(r: Point) -> None:
    """
    Checks point, throws if not on curve
    """
def point_eq(a: Point, b: Point) -> bool:
    """
    Compares EC points
    """
def point_add_into(r: Point | None, a: Point, b: Point) -> Point:
    """
    Adds EC points
    """
def point_sub_into(r: Point | None, a: Point, b: Point) -> Point:
    """
    Subtracts EC points
    """
def ge25519_mul8(r: Point | None, p: Point) -> Point:
    """
    EC point * 8
    """
def ge25519_double_scalarmult_vartime_into(
    r: Point | None, p1: Point, s1: Scalar, s2: Scalar
) -> Point:
    """
    s1 * G + s2 * p1
    """
def scalarmult_base_into(
    r: Point | None, s: Scalar | int
) -> Point:
    """
    s * G
    """
def scalarmult_into(
    r: Point | None, p: Point, s: Scalar | int
) -> Point:
    """
    s * p
    """
def encodepoint_into(r: bytes | None, p: Point, offset: int = 0) -> bytes:
    """
    Point compression
    """
def decodepoint_into(
    r: Point | None, buff: bytes, offset: int = 0
) -> Point:
    """
    Point decompression
    """
def xmr_base58_addr_encode_check(tag: int, buff: bytes) -> str:
    """
    Monero block base 58 encoding
    """
def xmr_base58_addr_decode_check(buff: bytes) -> tuple[bytes, int]:
    """
    Monero block base 58 decoding, returning (decoded, tag) or raising on
    error.
    """
def random_scalar(r: Scalar | None = None) -> Scalar:
    """
    Generates a random scalar
    """
def fast_hash_into(
   r: bytes | None,
   buff: bytes,
   length: int | None = None,
   offset: int = 0,
) -> bytes:
    """
    XMR fast hash
    """
def hash_to_point_into(
    r: Point | None,
    buff: bytes,
    length: int | None = None,
    offset: int = 0,
) -> Point:
    """
    XMR hashing to EC point
    """
def hash_to_scalar_into(
   r: Scalar | None,
   buff: bytes,
   length: int | None = None,
   offset: int = 0,
) -> Scalar:
    """
    XMR hashing to EC scalar
    """
def xmr_derivation_to_scalar(
    r: Scalar | None, p: Point, output_index: int
) -> Scalar:
    """
    H_s(derivation || varint(output_index))
    """
def xmr_generate_key_derivation(
    r: Point | None, A: Point, b: Scalar
) -> Point:
    """
    8*(key2*key1)
    """
def xmr_derive_private_key(
    r: Scalar | None, deriv: Point, idx: int, base: Scalar
) -> Scalar:
    """
    base + H_s(derivation || varint(output_index))
    """
def xmr_derive_public_key(
    r: Point | None, deriv: Point, idx: int, base: Point
) -> Point:
    """
    H_s(derivation || varint(output_index))G + base
    """
def add_keys2_into(
    r: Point | None, a: Scalar, b: Scalar, B: Point
) -> Point:
    """
    aG + bB, G is basepoint
    """
def add_keys3_into(
    r: Point | None, a: Scalar, A: Point, b: Scalar, B: Point
) -> Point:
    """
    aA + bB
    """
def xmr_get_subaddress_secret_key(
    r: Scalar | None, major: int, minor: int, m: Scalar
) -> Scalar:
    """
    Hs(SubAddr || a || index_major || index_minor)
    """
def gen_commitment_into(r: Point | None, a: Scalar, amount: int) -> Point:
    """
    aG + amount * H
    """
def ct_equals(a: bytes, b: bytes) -> bool:
    """
    Constant time buffer comparison
    """
BP_GI_PLUS_PRE: bytes
BP_HI_PLUS_PRE: bytes
