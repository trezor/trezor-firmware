use core::ops::Deref;
use pasta_curves::{arithmetic::FieldExt, group::ff::PrimeField, Fp};

use crate::micropython::{
    ffi,
    gc::Gc,
    map::Map,
    obj::Obj,
    qstr::Qstr,
    typ::Type,
    util,
    wrap::{Wrappable, Wrapped},
};

pub static FP_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_Fp,
    locals: &obj_dict!(obj_map! {
        Qstr::MP_QSTR_to_bytes => obj_fn_1!(fp_to_bytes).as_obj(),
    }),
    make_new_fn: super::common::ff_from_bytes::<Fp>,
    binary_op_fn: fp_binary_op,
};

impl Wrappable for Fp {
    fn obj_type() -> &'static Type {
        &FP_TYPE
    }
}

unsafe extern "C" fn fp_to_bytes(self_in: Obj) -> Obj {
    let block = || {
        let this: Gc<Wrapped<Fp>> = self_in.try_into()?;
        let bytes: [u8; 32] = this.deref().inner().to_repr();
        bytes.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

unsafe extern "C" fn fp_binary_op(op: ffi::mp_binary_op_t, this: Obj, other: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Fp>>::try_from(this)?;
        let this = this.deref().inner();
        match op {
            ffi::mp_binary_op_t_MP_BINARY_OP_ADD => {
                let other = Gc::<Wrapped<Fp>>::try_from(other)?;
                let other = other.deref().inner();
                (this + other).wrap()
            }
            _ => Ok(Obj::const_null()),
        }
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub unsafe extern "C" fn to_base(bytes: Obj) -> Obj {
    let block = || {
        let bytes: [u8; 64] = bytes.try_into()?;
        let elem = Fp::from_bytes_wide(&bytes);
        elem.wrap()
    };
    unsafe { util::try_or_raise(block) }
}
