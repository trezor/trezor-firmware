use crate::{
    error::Error,
    micropython::{map::Map, module::Module, obj::Obj, qstr::Qstr},
    storagedevice::field::Field,
    util,
};

use cstr_core::cstr;

use core::convert::TryFrom;

const APP_RECOVERY: u8 = 0x02;

const _DEFAULT_SLIP39_GROUP_COUNT: u8 = 0x01;

const _IN_PROGRESS: Field<bool> = Field::private(APP_RECOVERY, 0x00);
const _DRY_RUN: Field<bool> = Field::private(APP_RECOVERY, 0x01);
const _SLIP39_IDENTIFIER: Field<u16> = Field::private(APP_RECOVERY, 0x03);
const _SLIP39_THRESHOLD: Field<u16> = Field::private(APP_RECOVERY, 0x04);
const _REMAINING: Field<u8> = Field::private(APP_RECOVERY, 0x05);
const _SLIP39_ITERATION_EXPONENT: Field<u8> = Field::private(APP_RECOVERY, 0x06);
const _SLIP39_GROUP_COUNT: Field<u8> = Field::private(APP_RECOVERY, 0x07);

// # Deprecated Keys:
// # _WORD_COUNT                = const(0x02)  # int

extern "C" fn storagerecovery_is_in_progress() -> Obj {
    let block = || _IN_PROGRESS.get_result();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_set_in_progress(val: Obj) -> Obj {
    let block = || {
        _IN_PROGRESS.set(bool::try_from(val)?)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_is_dry_run() -> Obj {
    let block = || {
        _require_progress()?;
        _DRY_RUN.get_result()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_set_dry_run(val: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        _DRY_RUN.set(bool::try_from(val)?)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_get_slip39_identifier() -> Obj {
    let block = || {
        _require_progress()?;
        _SLIP39_IDENTIFIER.get_result()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_set_slip39_identifier(identifier: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        _SLIP39_IDENTIFIER.set(u16::try_from(identifier)?)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_get_slip39_iteration_exponent() -> Obj {
    let block = || {
        _require_progress()?;
        _SLIP39_ITERATION_EXPONENT.get_result()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_set_slip39_iteration_exponent(exponent: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        _SLIP39_ITERATION_EXPONENT.set(u8::try_from(exponent)?)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_get_slip39_group_count() -> Obj {
    let block = || {
        _require_progress()?;
        _SLIP39_GROUP_COUNT.get_result()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagerecovery_set_slip39_group_count(group_count: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        _SLIP39_GROUP_COUNT.set(u8::try_from(group_count)?)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

fn _require_progress() -> Result<(), Error> {
    let progress = _IN_PROGRESS.get().unwrap_or(false);
    if !progress {
        // TODO: how to raise RuntimeError?
        Err(Error::ValueError(cstr!("Recovery not in progress")))
    } else {
        Ok(())
    }
}

#[no_mangle]
pub static mp_module_trezorstoragerecovery: Module = obj_module! {
    Qstr::MP_QSTR___name_recovery__ => Qstr::MP_QSTR_trezorstoragerecovery.to_obj(),

    /// def is_in_progress() -> bool:
    ///     """Whether recovery is in progress."""
    Qstr::MP_QSTR_is_in_progress => obj_fn_0!(storagerecovery_is_in_progress).as_obj(),

    /// def set_in_progress(val: bool) -> None:
    ///     """Set in progress."""
    Qstr::MP_QSTR_set_in_progress => obj_fn_1!(storagerecovery_set_in_progress).as_obj(),

    /// def is_dry_run() -> bool:
    ///     """Whether recovery is dry - just a test."""
    Qstr::MP_QSTR_is_dry_run => obj_fn_0!(storagerecovery_is_dry_run).as_obj(),

    /// def set_dry_run(val: bool) -> None:
    ///     """Set the dry run."""
    Qstr::MP_QSTR_set_dry_run => obj_fn_1!(storagerecovery_set_dry_run).as_obj(),

    /// def get_slip39_identifier() -> int | None:
    ///     """Get slip39 identifier."""
    Qstr::MP_QSTR_get_slip39_identifier => obj_fn_0!(storagerecovery_get_slip39_identifier).as_obj(),

    /// def set_slip39_identifier(identifier: int) -> None:
    ///     """Set slip39 identifier."""
    Qstr::MP_QSTR_set_slip39_identifier => obj_fn_1!(storagerecovery_set_slip39_identifier).as_obj(),

    /// def get_slip39_iteration_exponent() -> int | None:
    ///     """Get slip39 iteration exponent."""
    Qstr::MP_QSTR_get_slip39_iteration_exponent => obj_fn_0!(storagerecovery_get_slip39_iteration_exponent).as_obj(),

    /// def set_slip39_iteration_exponent(exponent: int) -> None:
    ///     """Set slip39 iteration exponent."""
    Qstr::MP_QSTR_set_slip39_iteration_exponent => obj_fn_1!(storagerecovery_set_slip39_iteration_exponent).as_obj(),

    /// def get_slip39_group_count() -> int:
    ///     """Get slip39 group count."""
    Qstr::MP_QSTR_get_slip39_group_count => obj_fn_0!(storagerecovery_get_slip39_group_count).as_obj(),

    /// def set_slip39_group_count(group_count: int) -> None:
    ///     """Set slip39 group count."""
    Qstr::MP_QSTR_set_slip39_group_count => obj_fn_1!(storagerecovery_set_slip39_group_count).as_obj(),
};
