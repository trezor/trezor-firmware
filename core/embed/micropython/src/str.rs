use core::ffi::CStr;

use crate::gc::Gc;
use crate::py_object::HasBaseType;
use crate::typ::Type;
use crate::{Error, Obj, ffi};

pub type Str = ffi::mp_obj_str_t;

// SAFETY: Str type is a builtin and therefore has the right layout.
unsafe impl HasBaseType for Str {
    fn obj_type() -> &'static Type {
        unsafe { &ffi::mp_type_str }
    }
}

/// Create a Python `str` from a ROM based null-terminated C string.
///
/// Because the from-value is 'static, we can avoid re-allocating it,
/// we only create the Str object.
impl From<&'static CStr> for Str {
    fn from(value: &'static CStr) -> Self {
        // Values stolen from mp_obj_new_exception_msg.
        Self {
            base: Self::obj_type().as_base(),
            len: value.to_bytes().len(),
            data: value.as_ptr().cast(),
            // NOTE: when MICROPY_ROM_TEXT_COMPRESSION is enabled, we _could_ be
            // lazy and not compute the hash. We avoid this small optimization
            // to simplify macro-to-rust conversion.
            hash: unsafe { ffi::qstr_compute_hash(value.as_ptr().cast(), value.to_bytes().len()) },
        }
    }
}

/// ROM null-terminated strings can be converted to `str` MicroPython objects
/// without making a copy on the heap, only allocating the `mp_obj_str_t`
/// struct.
impl TryFrom<&'static CStr> for Obj {
    type Error = Error;

    fn try_from(val: &'static CStr) -> Result<Self, Self::Error> {
        Ok(Gc::new(Str::from(val))?.into())
    }
}
