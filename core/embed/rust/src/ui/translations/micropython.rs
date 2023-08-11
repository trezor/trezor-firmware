use crate::{
    error::Error,
    micropython::{
        ffi,
        obj::{Obj, ObjBase},
        qstr::Qstr,
        typ::Type,
        util,
    },
};

use super::{get_language_name, tr};

extern "C" fn translate_attr_fn(_self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
    let block = || {
        let arg = unsafe { dest.read() };
        if !arg.is_null() {
            // Null destination would mean a `setattr`.
            return Err(Error::TypeError);
        }
        let attr = Qstr::from_u16(attr as u16);
        unsafe { dest.write(TR_OBJ.getattr(attr)?) };
        Ok(())
    };
    unsafe { util::try_or_raise(block) }
}

#[repr(C)]
pub struct TrObj {
    base: ObjBase,
}

static TR_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_TR,
    attr_fn: translate_attr_fn,
};

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for TrObj {}

impl TrObj {
    fn obj_type() -> &'static Type {
        &TR_TYPE
    }

    fn getattr(&self, attr: Qstr) -> Result<Obj, Error> {
        tr(attr.as_str()).try_into()
    }

    /// Convert TrObj to a MicroPython object
    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - There's nothing to mutate.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }
}

/// Translations object callable from micropython.
pub static TR_OBJ: TrObj = TrObj {
    base: TR_TYPE.as_base(),
};

/// Language name getter callable from micropython.
pub extern "C" fn language_name_obj() -> Obj {
    let block = || {
        if let Some(lang) = get_language_name() {
            lang.try_into()
        } else {
            Ok(Obj::const_none())
        }
    };
    unsafe { util::try_or_raise(block) }
}
