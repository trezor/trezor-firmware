use cstr_core::cstr;
use pasta_curves::group::ff;

use crate::{
    error::Error,
    micropython::{map::Map, obj::Obj, typ::Type, util, wrap::Wrappable},
};

pub unsafe extern "C" fn ff_from_bytes<F: Wrappable + ff::PrimeField<Repr = [u8; 32]>>(
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
        let elem = F::from_repr(bytes);
        match Option::<F>::from(elem) {
            Some(e) => e.wrap(),
            None => Err(Error::ValueError(cstr!("Conversion failed"))),
        }
    };
    unsafe { util::try_with_args_and_kwargs_inline(n_args, n_kw, args, block) }
}
