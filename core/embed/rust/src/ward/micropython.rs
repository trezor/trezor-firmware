use super::error::WARD_EXCEPTION_TYPE;
use super::store::{Buffer, Scope, Store, WalletId};
use crate::micropython::buffer::get_buffer;
use crate::micropython::macros::{obj_fn_3, obj_fn_var, obj_module};
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;
use crate::micropython::{util, Error, Obj};

fn store<'a>(wallet_id: &'a [u8], app: &'a [u8]) -> Result<Store<'a>, Error> {
    let wallet_id: &WalletId = wallet_id
        .try_into()
        .map_err(|_| Error::ValueError(c"Invalid wallet id"))?;
    Ok(Store::new(Scope::new(wallet_id, app)?)?)
}

extern "C" fn ward_get(wallet_id: Obj, app: Obj, key: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (wallet_id, app, key) =
            unsafe { (get_buffer(wallet_id)?, get_buffer(app)?, get_buffer(key)?) };
        let mut buf = Buffer::new();
        store(wallet_id, app)?.get(key, &mut buf)?.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_next_entry(wallet_id: Obj, app: Obj, cursor: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (wallet_id, app) = unsafe { (get_buffer(wallet_id)?, get_buffer(app)?) };
        let store = store(wallet_id, app)?;
        let cursor: u8 = cursor.try_into()?;
        let mut buf = Buffer::new();
        match store.next(cursor, &mut buf)? {
            Some((next, record)) => (next, record.key, record.value).try_into(),
            None => Ok(Obj::const_none()),
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_set(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        // SAFETY: references are discarded at the end of this block.
        let (wallet_id, app, key, value) = unsafe {
            (
                get_buffer(args[0])?,
                get_buffer(args[1])?,
                get_buffer(args[2])?,
                get_buffer(args[3])?,
            )
        };
        store(wallet_id, app)?.set(key, value)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn ward_delete(wallet_id: Obj, app: Obj, key: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (wallet_id, app, key) =
            unsafe { (get_buffer(wallet_id)?, get_buffer(app)?, get_buffer(key)?) };
        Ok(store(wallet_id, app)?.delete(key)?.into())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezorward: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorward.to_obj(),

    /// WardError: type[Exception]
    Qstr::MP_QSTR_WardError => WARD_EXCEPTION_TYPE.as_type().as_obj(),

    /// def get(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes) -> bytes | None:
    ///     """
    ///     Return the value stored under `key` for the given wallet and app,
    ///     or None if there is no such record.
    ///     """
    Qstr::MP_QSTR_get => obj_fn_3!(ward_get).as_obj(),

    /// def next_entry(wallet_id: AnyBytes, app: AnyBytes, cursor: int) -> tuple[int, bytes, bytes] | None:
    ///     """
    ///     Return `(next_cursor, key, value)` of the next record of the given
    ///     wallet and app from `cursor` on, or None if there is none left.
    ///     The cursor is opaque: iteration starts with 0 and continues with
    ///     `next_cursor`. The order of the records is unspecified, and so are
    ///     the results if any store is modified in between.
    ///     """
    Qstr::MP_QSTR_next_entry => obj_fn_3!(ward_next_entry).as_obj(),

    /// def set(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes, value: AnyBytes) -> None:
    ///     """
    ///     Store `value` under `key` for the given wallet and app, replacing an
    ///     existing value in place. Raise WardError if the record does not fit.
    ///     """
    Qstr::MP_QSTR_set => obj_fn_var!(4, 4, ward_set).as_obj(),

    /// def delete(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes) -> bool:
    ///     """
    ///     Delete the record stored under `key` for the given wallet and app.
    ///     Return whether a record was deleted.
    ///     """
    Qstr::MP_QSTR_delete => obj_fn_3!(ward_delete).as_obj(),
};
