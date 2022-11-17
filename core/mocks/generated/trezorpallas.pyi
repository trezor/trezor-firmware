from typing import *


# rust/src/zcash_primitives/pallas/mod.rs
def to_base(x: bytes) -> Fp:
    """https://zips.z.cash/protocol/protocol.pdf#orchardkeycomponents"""


# rust/src/zcash_primitives/pallas/mod.rs
def to_scalar(x: bytes) -> Scalar:
    """https://zips.z.cash/protocol/protocol.pdf#orchardkeycomponents"""


# rust/src/zcash_primitives/pallas/mod.rs
def group_hash(domain: str, message: bytes) -> Point:
    """https://zips.z.cash/protocol/protocol.pdf#concretegrouphashpallasandvesta"""


# rust/src/zcash_primitives/pallas/mod.rs
def scalar_from_i64(x: int) -> Scalar:
    """Converts integer to Scalar."""


# rust/src/zcash_primitives/pallas/mod.rs
class Fp:
    """Pallas base field."""
    def __init__(self, repr: bytes) -> None:
        ...
    def to_bytes(self) -> bytes:
        ...


# rust/src/zcash_primitives/pallas/mod.rs
class Scalar:
    """Pallas scalar field."""
    def __init__(self, repr: bytes) -> None:
        ...
    def to_bytes(self) -> bytes:
        ...
    def __mul__(self, other: Point) -> Point:
        ...
    def __add__(self, other: Scalar) -> Scalar:
        ...
    def __neg__(self) -> Point:
        ...
    def __bool__(self) -> bool:
        ...


# rust/src/zcash_primitives/pallas/mod.rs
class Point:
    """Pallas point."""
    def __init__(self, repr: bytes) -> None:
        ...
    def to_bytes(self) -> bytes:
        ...
    def extract(self) -> Fp:
        ...
    def is_identity(self) -> bool:
        ...
    def __add__(self, other: Point) -> Point:
        ...
    def __neg__(self) -> Point:
        ...


# rust/src/zcash_primitives/pallas/mod.rs
class generators:
    SPENDING_KEY_BASE: Point
    NULLIFIER_K_BASE: Point
    VALUE_COMMITMENT_VALUE_BASE: Point
    VALUE_COMMITMENT_RANDOMNESS_BASE: Point
    NOTE_COMMITMENT_BASE: Point
    NOTE_COMMITMENT_Q: Point
    IVK_COMMITMENT_BASE: Point
    IVK_COMMITMENT_Q: Point
