use super::error::WARD_EXCEPTION_TYPE;
use crate::micropython::macros::{obj_fn_3, obj_fn_var, obj_module};
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;
use crate::micropython::{util, Error, Obj};

extern "C" fn ward_get(_wallet_id: Obj, _app: Obj, _key: Obj) -> Obj {
    let block = || -> Result<Obj, Error> { Err(Error::NotImplementedError) };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_next_entry(_wallet_id: Obj, _app: Obj, _cursor: Obj) -> Obj {
    let block = || -> Result<Obj, Error> { Err(Error::NotImplementedError) };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_set(n_args: usize, args: *const Obj) -> Obj {
    let block =
        |_args: &[Obj], _kwargs: &Map| -> Result<Obj, Error> { Err(Error::NotImplementedError) };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn ward_delete(_wallet_id: Obj, _app: Obj, _key: Obj) -> Obj {
    let block = || -> Result<Obj, Error> { Err(Error::NotImplementedError) };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezorward: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorward.to_obj(),

    /// WardError: type[Exception]
    Qstr::MP_QSTR_WardError => WARD_EXCEPTION_TYPE.as_type().as_obj(),

    /// def get(wallet_id: AnyBytes, app: int, key: AnyBytes) -> bytes | None:
    ///     """
    ///     Return the value stored under `key` for the given wallet and app,
    ///     or None if there is no such record.
    ///     """
    Qstr::MP_QSTR_get => obj_fn_3!(ward_get).as_obj(),

    /// def next_entry(wallet_id: AnyBytes, app: int, cursor: int) -> tuple[int, bytes, bytes] | None:
    ///     """
    ///     Return `(next_cursor, key, value)` of the first record of the given
    ///     wallet and app at or after `cursor`, or None if there is none left.
    ///     Iteration starts with cursor 0 and continues with `next_cursor`.
    ///     """
    Qstr::MP_QSTR_next_entry => obj_fn_3!(ward_next_entry).as_obj(),

    /// def set(wallet_id: AnyBytes, app: int, key: AnyBytes, value: AnyBytes) -> None:
    ///     """
    ///     Store `value` under `key` for the given wallet and app, replacing an
    ///     existing value in place. Raise WardError if the record does not fit.
    ///     """
    Qstr::MP_QSTR_set => obj_fn_var!(4, 4, ward_set).as_obj(),

    /// def delete(wallet_id: AnyBytes, app: int, key: AnyBytes) -> bool:
    ///     """
    ///     Delete the record stored under `key` for the given wallet and app.
    ///     Return whether a record was deleted.
    ///     """
    Qstr::MP_QSTR_delete => obj_fn_3!(ward_delete).as_obj(),
};
