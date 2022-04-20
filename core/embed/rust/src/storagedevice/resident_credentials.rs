use crate::{
    error::Error,
    micropython::{buffer::Buffer, map::Map, module::Module, obj::Obj, qstr::Qstr},
    trezorhal::storage_field::{Field, FieldGetSet, FieldOpsBase},
    util,
};
use cstr_core::cstr;
use heapless::Vec;

const APP_WEBAUTHN: u8 = 0x04;

const RESIDENT_CREDENTIAL_START_KEY: u8 = 1;
const MAX_RESIDENT_CREDENTIALS: u8 = 100;

extern "C" fn get(index: Obj) -> Obj {
    let block = || {
        let index = index.try_into()?;
        _require_valid_index(index)?;

        Field::<Vec<u8, 4096>>::private(APP_WEBAUTHN, index + RESIDENT_CREDENTIAL_START_KEY)
            .get()
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set(index: Obj, data: Obj) -> Obj {
    let block = || {
        let index = index.try_into()?;
        _require_valid_index(index)?;
        let data: Buffer = data.try_into()?;
        Field::<Vec<u8, 4096>>::private(APP_WEBAUTHN, index + RESIDENT_CREDENTIAL_START_KEY)
            .set(data.try_into()?)?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn delete(index: Obj) -> Obj {
    let block = || {
        let index = index.try_into()?;
        _require_valid_index(index)?;
        Field::<Vec<u8, 4096>>::private(APP_WEBAUTHN, index + RESIDENT_CREDENTIAL_START_KEY)
            .delete()?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn delete_all() -> Obj {
    let block = || {
        for index in 0..MAX_RESIDENT_CREDENTIALS {
            Field::<Vec<u8, 4096>>::private(APP_WEBAUTHN, index + RESIDENT_CREDENTIAL_START_KEY)
                .delete()?;
        }
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

fn _require_valid_index(index: u8) -> Result<(), Error> {
    if index >= MAX_RESIDENT_CREDENTIALS {
        Err(Error::ValueError(cstr!("Invalid credentials index")))
    } else {
        Ok(())
    }
}

#[no_mangle]
pub static mp_module_trezorstorageresidentcredentials: Module = obj_module! {
    Qstr::MP_QSTR___name_residentcredentials__ => Qstr::MP_QSTR_trezorstorageresidentcredentials.to_obj(),

    /// def get(index: int) -> bytes | None:
    ///     """Get credentials."""
    Qstr::MP_QSTR_get => obj_fn_1!(get).as_obj(),

    /// def set(index: int, data: bytes) -> None:
    ///     """Set credentials."""
    Qstr::MP_QSTR_set => obj_fn_2!(set).as_obj(),

    /// def delete(index: int) -> None:
    ///     """Delete credentials."""
    Qstr::MP_QSTR_delete => obj_fn_1!(delete).as_obj(),

    /// def delete_all() -> None:
    ///     """Delete all credentials."""
    Qstr::MP_QSTR_delete_all => obj_fn_0!(delete_all).as_obj(),
};
