use core::ops::Deref;
use cstr_core::cstr;
use pasta_curves::{
    arithmetic::{CurveAffine, CurveExt},
    group::{Curve, Group, GroupEncoding},
    pallas::Point,
    Fp,
};

use crate::{
    error::Error,
    micropython::{
        buffer::{Buffer, StrBuffer},
        ffi,
        gc::Gc,
        map::Map,
        obj::Obj,
        qstr::Qstr,
        typ::Type,
        util,
        wrap::{Wrappable, Wrapped},
    },
};

pub static POINT_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_Point,
    locals: &obj_dict!(obj_map! {
            Qstr::MP_QSTR_extract => obj_fn_1!(point_extract).as_obj(),
            Qstr::MP_QSTR_to_bytes => obj_fn_1!(point_to_bytes).as_obj(),
            Qstr::MP_QSTR_is_identity => obj_fn_1!(point_is_identity).as_obj(),
    }),
    make_new_fn: point_from_bytes,
    unary_op_fn: point_unary_op,
    binary_op_fn: point_binary_op,
};

impl Wrappable for Point {
    fn obj_type() -> &'static Type {
        &POINT_TYPE
    }
}

unsafe extern "C" fn point_from_bytes(
    _type_: *const Type,
    n_args: usize,
    n_kw: usize,
    args: *const Obj,
) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 1 {
            return Err(Error::TypeError);
        }
        let bytes: [u8; 32] = args[0].try_into()?;
        let point = Point::from_bytes(&bytes);
        match Option::<Point>::from(point) {
            Some(p) => p.wrap(),
            None => Err(Error::ValueError(cstr!("Conversion failed"))),
        }
    };
    unsafe { util::try_with_args_and_kwargs_inline(n_args, n_kw, args, block) }
}

unsafe extern "C" fn point_unary_op(op: ffi::mp_unary_op_t, this: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Point>>::try_from(this)?;
        let this = this.deref().inner();
        match op {
            ffi::mp_unary_op_t_MP_UNARY_OP_NEGATIVE => (-this).wrap(),
            _ => Ok(Obj::const_null()),
        }
    };
    unsafe { util::try_or_raise(block) }
}

unsafe extern "C" fn point_binary_op(op: ffi::mp_binary_op_t, this: Obj, other: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Point>>::try_from(this)?;
        let this = this.deref().inner();
        match op {
            ffi::mp_binary_op_t_MP_BINARY_OP_ADD => {
                let other = Gc::<Wrapped<Point>>::try_from(other)?;
                let other = other.deref().inner();
                (this + other).wrap()
            }
            ffi::mp_binary_op_t_MP_BINARY_OP_EQUAL => {
                let other = Gc::<Wrapped<Point>>::try_from(other)?;
                let other = other.deref().inner();
                Ok((this == other).into())
            }
            ffi::mp_binary_op_t_MP_BINARY_OP_NOT_EQUAL => {
                let other = Gc::<Wrapped<Point>>::try_from(other)?;
                let other = other.deref().inner();
                Ok((this != other).into())
            }
            _ => Ok(Obj::const_null()),
        }
    };
    unsafe { util::try_or_raise(block) }
}

unsafe extern "C" fn point_extract(self_in: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Point>>::try_from(self_in)?;
        let elem = this
            .deref()
            .inner()
            .to_affine()
            .coordinates()
            .map(|c| *c.x())
            .unwrap_or_else(Fp::zero);
        elem.wrap()
    };
    unsafe { util::try_or_raise(block) }
}

unsafe extern "C" fn point_is_identity(self_in: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Point>>::try_from(self_in)?;
        let this = this.deref().inner();
        Ok((this == &Point::identity()).into())
    };
    unsafe { util::try_or_raise(block) }
}

unsafe extern "C" fn point_to_bytes(self_in: Obj) -> Obj {
    let block = || {
        let this = Gc::<Wrapped<Point>>::try_from(self_in)?;
        let bytes: [u8; 32] = this.deref().inner().to_bytes();
        bytes.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub unsafe extern "C" fn group_hash(domain: Obj, message: Obj) -> Obj {
    let block = || {
        let domain: StrBuffer = domain.try_into()?;
        let message: Buffer = message.try_into()?;
        let point = Point::hash_to_curve(domain.deref(), message.deref());
        point.wrap()
    };
    unsafe { util::try_or_raise(block) }
}
