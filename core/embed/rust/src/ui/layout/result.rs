use crate::micropython::{
    obj::{Obj, ObjBase},
    qstr::Qstr,
    typ::Type,
};

#[repr(C)]
pub struct ResultObj {
    base: ObjBase,
}

impl ResultObj {
    /// Convert ResultObj to a MicroPython object.
    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - There's nothing to mutate.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for ResultObj {}

static CONFIRMED_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_CONFIRMED, };
static CANCELLED_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_CANCELLED, };
static INFO_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_INFO, };

pub static CONFIRMED: ResultObj = ResultObj {
    base: CONFIRMED_TYPE.as_base(),
};
pub static CANCELLED: ResultObj = ResultObj {
    base: CANCELLED_TYPE.as_base(),
};
pub static INFO: ResultObj = ResultObj {
    base: INFO_TYPE.as_base(),
};
