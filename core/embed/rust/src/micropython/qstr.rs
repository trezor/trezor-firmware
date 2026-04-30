use core::convert::TryFrom;
use core::slice;

use super::{ffi, Error, Obj};

/// Identifier trait for Qstr numeric ids.
///
/// Users of the `micropython` module must generate a full set of qstrings used
/// throughout both MicroPython and their own codebase (via MPy's qstr
/// collection mechanism), and then implement this trait on type(s) that
/// represent those qstring identifiers.
///
/// One way to do that is use MicroPython's collection script to generate
/// `qstrdefs.generated.h` and generate a Rust enum from those values.
///
/// The [`crate::micropython`] module cannot provide that enum, because its
/// values depend on the full codebase of the caller's MicroPython project. That
/// would introduce a circular dependency: you could not build the `micropython`
/// module without knowing the code which calls it.
///
/// Instead, the user code shall implement `QstrValue` on the generated enum (or
/// whatever other choice of type). The implementation provides two-way
/// conversion between raw qstr id numbers, and a representation type.
///
/// The trait must be `const` in order to be usable when constructing static
/// objects (module definitions, etc.)
pub const trait QstrValue: Copy {
    /// Convert a numeric qstr identifier to a QstrValue object.
    fn from_u16(val: u16) -> Self;

    /// Get a numeric qstr identifier from a QstrValue object.
    fn to_u16(self) -> u16;

    /// Convert a QstrValue object to an `Attribute`.
    fn to_attribute(self) -> Attribute {
        Attribute(self.to_u16() as _)
    }
}

/// Extension trait for QstrValue objects.
///
/// Provides a `to_str` method that converts a QstrValue object to a string.
pub trait QstrExt {
    /// Return a string corresponding to the qstr value.
    fn to_str(self) -> &'static str;
}

impl<T: QstrValue> QstrExt for T {
    fn to_str(self) -> &'static str {
        self.to_attribute().to_str()
    }
}

/// A reusable `TryFrom<Obj>` implementation for QstrValues.
///
/// Place the following next to your `QstrValue` concrete type:
///
/// ```rust,ignore
/// impl TryFrom<Obj> for $your_qstr_value_type {
///     type Error = Error;
///
///     fn try_from(value: Obj) -> Result<Self, Self::Error> {
///         qstr::try_from_obj(value)
///     }
/// }
/// ```
pub fn try_from_obj<T: QstrValue>(obj: Obj) -> Result<T, Error> {
    let attr: Attribute = obj.try_into()?;
    Ok(T::from_u16(attr.into_raw() as _))
}

impl<T: QstrValue> From<T> for Obj {
    fn from(value: T) -> Self {
        value.to_attribute().to_obj()
    }
}

/// MicroPython attribute type.
///
/// A value type for arguments, struct fields, function returns, etc.,
/// representing MicroPython qstrings.
///
/// MicroPython itself is somewhat inconsistent in this:
///
/// * most of the API surface relies on `Obj`s and does conversions internally
/// * `Map` elements can have keys of an arbitrary `Obj`, but attribute lookups
///   only work correctly if the `Obj` is a qstr
/// * some struct members (`Type::name`) are numeric types (`u16`)
/// * certain features (`qstr.h`, `attrtuple`) require the use of explicit
///   `qstr` type
///
/// `Attribute` is a newtype wrapper over `qstr`, which is typically a typedef
/// over `usize` (so we can't put impls directly on `qstr`). It is also
/// `repr(transparent)`, so `&[Attribute]` is legal where `&[qstr]` is expected
/// (such as in attrtuples).
#[derive(Debug, Copy, Clone, PartialEq, Eq, Hash)]
#[repr(transparent)]
pub struct Attribute(ffi::qstr);

impl Attribute {
    /// Lower an `Attribute` into the inner `qstr` value.
    pub const fn into_raw(self) -> ffi::qstr {
        self.0
    }

    /// Construct an `Attribute` from the inner `qstr` value.
    pub const fn from_raw(raw: ffi::qstr) -> Self {
        Self(raw)
    }

    /// Construct an `Attribute` from a raw qstr id number.
    pub const fn from_u16(val: u16) -> Self {
        Self(val as _)
    }

    /// Return a string corresponding to the qstr id.
    pub fn to_str(self) -> &'static str {
        let mut len = 0usize;
        let slice = unsafe {
            // SAFETY: qstr_data should always return a valid string, even for unknown ids.
            let ptr = ffi::qstr_data(self.0, &mut len as *mut _);
            slice::from_raw_parts(ptr, len)
        };
        // SAFETY: Qstr pools are either ROM-based or permanently allocated in the GC
        // arena. The MicroPython runtime holds the respective head pointers so we don't
        // need to care.
        unwrap!(str::from_utf8(slice))
    }

    /// Convert an `Attribute` to an `Obj`.
    pub const fn to_obj(self) -> Obj {
        // SAFETY:
        // Micropython compiled with `MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_A`.
        //
        // micropython/py/obj.h
        // ```c
        // #define MP_OBJ_NEW_QSTR(qst)  ((mp_obj_t)((((mp_uint_t)(qst)) << 3) | 2))
        // ```
        let bits = (self.0 << 3) | 2;
        unsafe { Obj::from_bits(bits) }
    }

    /// Extract the qstr id bits from `Obj`'s bits.
    ///
    /// Assumes but does not check that the passed bits represent a `qstr`. If
    /// they don't, the result is a spurious `Attribute` with unspecified,
    /// possibly invalid id.
    const fn from_obj_bits(bits: cty::uintptr_t) -> Self {
        let bits = (bits >> 3) as u16; // See `Self::to_obj`.
        Self::from_u16(bits)
    }

    /// Construct an `Attribute` from a `QstrValue` object.
    pub const fn from_qstr_value<T: const QstrValue>(value: T) -> Self {
        Self::from_u16(value.to_u16())
    }
}

impl From<Attribute> for Obj {
    fn from(value: Attribute) -> Self {
        value.to_obj()
    }
}

impl TryFrom<Obj> for Attribute {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if value.is_qstr() {
            Ok(Self::from_obj_bits(value.as_bits()))
        } else {
            Err(Error::TypeError)
        }
    }
}

#[inline]
/// Const helper to convert a `QstrValue` object to a raw qstr id number.
///
/// Workaround for Rust's const trait limitations: a const fn is explicitly
/// valid to call in const contexts, where a method on an `impl QstrValue`
/// either may not be, or may require horrible typecasting boilerplate (which
/// itself may be legal but not supported by rustc in const contexts).
pub const fn qstr_value_to_u16<T: const QstrValue>(value: T) -> u16 {
    value.to_u16()
}

// XXX compatibility re-export
// The intention here is that after the crate split,
// `crate::micropython::qstr::Qstr` remains valid
pub use super::qstr_generated::Qstr;
