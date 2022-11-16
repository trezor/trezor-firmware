use core::ops::Deref;

use pasta_curves::{
    arithmetic::FieldExt,
    group::ff::{Field, PrimeField},
    pallas::{Point, Scalar},
};

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

pub static SCALAR_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_Scalar,
    locals: &obj_dict!(obj_map! {
            Qstr::MP_QSTR_to_bytes => obj_fn_1!(scalar_to_bytes).as_obj(),
    }),
    make_new_fn: super::common::ff_from_bytes::<Scalar>,
    unary_op_fn: scalar_unary_op,
    binary_op_fn: scalar_binary_op,
};

impl Wrappable for Scalar {
    fn obj_type() -> &'static Type {
        &SCALAR_TYPE
    }
}

unsafe extern "C" fn scalar_binary_op(op: ffi::mp_binary_op_t, this: Obj, other: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Scalar>>::try_from(this)?;
        let this = this.deref().inner();
        match op {
            ffi::mp_binary_op_t_MP_BINARY_OP_MULTIPLY => {
                let other = Gc::<Wrapped<Point>>::try_from(other)?;
                let other = other.deref().inner();
                (other * this).wrap()
            }
            ffi::mp_binary_op_t_MP_BINARY_OP_ADD => {
                let other = Gc::<Wrapped<Scalar>>::try_from(other)?;
                let other = other.deref().inner();
                (other + this).wrap()
            }
            _ => Ok(Obj::const_null()),
        }
    };
    unsafe { util::try_or_raise(block) }
}

unsafe extern "C" fn scalar_unary_op(op: ffi::mp_unary_op_t, this: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Scalar>>::try_from(this)?;
        let this = this.deref().inner();
        match op {
            ffi::mp_unary_op_t_MP_UNARY_OP_NEGATIVE => (-this).wrap(),
            ffi::mp_unary_op_t_MP_UNARY_OP_BOOL => Ok(bool::from(!this.is_zero()).into()),
            _ => Ok(Obj::const_null()),
        }
    };
    unsafe { util::try_or_raise(block) }
}

unsafe extern "C" fn scalar_to_bytes(self_in: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Scalar>>::try_from(self_in)?;
        let bytes: [u8; 32] = this.deref().inner().to_repr();
        bytes.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub unsafe extern "C" fn to_scalar(bytes: Obj) -> Obj {
    let block = || {
        let bytes: [u8; 64] = bytes.try_into()?;
        let elem = Scalar::from_bytes_wide(&bytes);
        elem.wrap()
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub unsafe extern "C" fn scalar_from_i64(n: Obj) -> Obj {
    let block = || {
        let n: i64 = n.try_into()?;
        if n >= 0 {
            Scalar::from(n as u64).wrap()
        } else {
            (-Scalar::from(-n as u64)).wrap()
        }
    };
    unsafe { util::try_or_raise(block) }
}
