use crate::micropython::{map::Map, module::Module, qstr::Qstr};

pub mod common;
mod fp;
mod generators;
mod point;
mod scalar;

#[no_mangle]
pub static mp_module_trezorpallas: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorpallas.to_obj(),
    /// def to_base(x: bytes) -> Fp:
    ///     """https://zips.z.cash/protocol/protocol.pdf#orchardkeycomponents"""
    Qstr::MP_QSTR_to_base => obj_fn_1!(fp::to_base).as_obj(),
    /// def to_scalar(x: bytes) -> Scalar:
    ///     """https://zips.z.cash/protocol/protocol.pdf#orchardkeycomponents"""
    Qstr::MP_QSTR_to_scalar => obj_fn_1!(scalar::to_scalar).as_obj(),
    /// def group_hash(domain: str, message: bytes) -> Point:
    ///     """https://zips.z.cash/protocol/protocol.pdf#concretegrouphashpallasandvesta"""
    Qstr::MP_QSTR_group_hash => obj_fn_2!(point::group_hash).as_obj(),
    /// def scalar_from_i64(x: int) -> Scalar:
    ///     """Converts integer to Scalar."""
    Qstr::MP_QSTR_scalar_from_i64 => obj_fn_1!(scalar::scalar_from_i64).as_obj(),
    /// class Fp:
    ///     """Pallas base field."""
    ///
    ///     def __init__(self, repr: bytes) -> None:
    ///         ...
    ///
    ///     def to_bytes(self) -> bytes:
    ///         ...
    Qstr::MP_QSTR_Fp => (&fp::FP_TYPE).as_obj(),
    /// class Scalar:
    ///     """Pallas scalar field."""
    ///
    ///     def __init__(self, repr: bytes) -> None:
    ///         ...
    ///
    ///     def to_bytes(self) -> bytes:
    ///         ...
    ///
    ///     def __mul__(self, other: Point) -> Point:
    ///         ...
    ///
    ///     def __add__(self, other: Scalar) -> Scalar:
    ///         ...
    ///
    ///     def __neg__(self) -> Point:
    ///         ...
    ///
    ///     def __bool__(self) -> bool:
    ///         ...
    Qstr::MP_QSTR_Scalar => (&scalar::SCALAR_TYPE).as_obj(),
    /// class Point:
    ///     """Pallas point."""
    ///
    ///     def __init__(self, repr: bytes) -> None:
    ///         ...
    ///
    ///     def to_bytes(self) -> bytes:
    ///         ...
    ///
    ///     def extract(self) -> Fp:
    ///         ...
    ///
    ///     def is_identity(self) -> bool:
    ///         ...
    ///
    ///     def __add__(self, other: Point) -> Point:
    ///         ...
    ///
    ///     def __neg__(self) -> Point:
    ///         ...
    Qstr::MP_QSTR_Point => (&point::POINT_TYPE).as_obj(),
    /// class generators:
    ///     SPENDING_KEY_BASE: Point
    ///     NULLIFIER_K_BASE: Point
    ///     VALUE_COMMITMENT_VALUE_BASE: Point
    ///     VALUE_COMMITMENT_RANDOMNESS_BASE: Point
    ///     NOTE_COMMITMENT_BASE: Point
    ///     NOTE_COMMITMENT_Q: Point
    ///     IVK_COMMITMENT_BASE: Point
    ///     IVK_COMMITMENT_Q: Point
    Qstr::MP_QSTR_generators => (&generators::GENERATORS_TYPE).as_obj(),
};
