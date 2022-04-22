use crate::{
    error::Error,
    micropython::{list::List, map::Map, module::Module, obj::Obj, qstr::Qstr},
    storagedevice::recovery_shares,
    trezorhal::storage_field::{Field, FieldGetSet, FieldOpsBase},
    util,
};
use cstr_core::cstr;
use heapless::Vec;

// The maximum number of shares/groups that can be created.
const MAX_SHARE_COUNT: usize = 16;
const MAX_GROUP_COUNT: usize = 16;

const DEFAULT_SLIP39_GROUP_COUNT: u8 = 1;

const APP_RECOVERY: u8 = 0x02;
const APP_RECOVERY_SHARES: u8 = 0x03;

const IN_PROGRESS: Field<bool> = Field::private(APP_RECOVERY, 0x00);
const DRY_RUN: Field<bool> = Field::private(APP_RECOVERY, 0x01);
// NOTE: 0x02 key was used in the past for WORD_COUNT. Not used anymore.
const SLIP39_IDENTIFIER: Field<u16> = Field::private(APP_RECOVERY, 0x03);
const SLIP39_THRESHOLD: Field<u16> = Field::private(APP_RECOVERY, 0x04);
const REMAINING: Field<Vec<u8, MAX_SHARE_COUNT>> = Field::private(APP_RECOVERY, 0x05);
const SLIP39_ITERATION_EXPONENT: Field<u8> = Field::private(APP_RECOVERY, 0x06);
const SLIP39_GROUP_COUNT: Field<u8> = Field::private(APP_RECOVERY, 0x07);

extern "C" fn is_in_progress() -> Obj {
    let block = || Ok(IN_PROGRESS.get().unwrap_or(false).into());
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_in_progress(val: Obj) -> Obj {
    let block = || IN_PROGRESS.set(val.try_into()?)?.try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn is_dry_run() -> Obj {
    let block = || {
        _require_progress()?;
        Ok(DRY_RUN.get().unwrap_or(false).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_dry_run(val: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        DRY_RUN.set(val.try_into()?)?.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_slip39_identifier() -> Obj {
    let block = || {
        _require_progress()?;
        Ok(SLIP39_IDENTIFIER.get().into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_slip39_identifier(identifier: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        SLIP39_IDENTIFIER.set(identifier.try_into()?)?.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_slip39_iteration_exponent() -> Obj {
    let block = || {
        _require_progress()?;
        Ok(SLIP39_ITERATION_EXPONENT.get().into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_slip39_iteration_exponent(exponent: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        SLIP39_ITERATION_EXPONENT
            .set(exponent.try_into()?)?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_slip39_group_count() -> Obj {
    let block = || {
        _require_progress()?;
        Ok(_get_slip39_group_count().into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_slip39_group_count(group_count: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        SLIP39_GROUP_COUNT.set(group_count.try_into()?)?.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_slip39_remaining_shares(group_index: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        let group_index: usize = group_index.try_into()?;

        if let Some(remaining) = REMAINING.get() {
            let amount = remaining[group_index];
            if amount == MAX_SHARE_COUNT as u8 {
                Ok(Obj::const_none())
            } else {
                Ok(amount.into())
            }
        } else {
            Ok(Obj::const_none())
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn fetch_slip39_remaining_shares() -> Obj {
    let block = || {
        _require_progress()?;

        let remaining = match REMAINING.get() {
            Some(remaining) => remaining,
            None => return Ok(Obj::const_none()),
        };

        let group_count = _get_slip39_group_count() as usize;
        if group_count == 0 {
            return Err(Error::ValueError(cstr!("There are no remaining shares")));
        }

        let remaining = remaining[..group_count]
            .iter()
            .cloned()
            .collect::<Vec<u8, MAX_SHARE_COUNT>>()
            .into_iter();
        List::from_iter(remaining).map(Into::into)
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_slip39_remaining_shares(shares_remaining: Obj, group_index: Obj) -> Obj {
    let block = || {
        _require_progress()?;
        let shares_remaining = shares_remaining.try_into()?;
        let group_index: usize = group_index.try_into()?;

        let group_count = _get_slip39_group_count() as usize;
        if group_count == 0 {
            return Err(Error::ValueError(cstr!("There are no remaining shares")));
        }

        let mut default_remaining: Vec<u8, MAX_SHARE_COUNT> = Vec::<u8, MAX_SHARE_COUNT>::new();
        for _ in 0..group_count {
            default_remaining.push(MAX_SHARE_COUNT as u8).unwrap();
        }
        let mut remaining = REMAINING.get().unwrap_or(default_remaining);
        remaining[group_index] = shares_remaining;

        REMAINING
            .set(Vec::from_slice(&remaining as &[u8]).unwrap())?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn end_progress() -> Obj {
    let block = || {
        _require_progress()?;

        IN_PROGRESS.delete()?;
        DRY_RUN.delete()?;
        SLIP39_IDENTIFIER.delete()?;
        SLIP39_THRESHOLD.delete()?;
        REMAINING.delete()?;
        SLIP39_ITERATION_EXPONENT.delete()?;
        SLIP39_GROUP_COUNT.delete()?;

        recovery_shares::delete_all_recovery_shares()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

fn _require_progress() -> Result<(), Error> {
    let progress = IN_PROGRESS.get().unwrap_or(false);
    if !progress {
        // TODO: how to raise RuntimeError?
        Err(Error::ValueError(cstr!("Recovery not in progress")))
    } else {
        Ok(())
    }
}

/// Helper because there is a default value in case it is missing
fn _get_slip39_group_count() -> u8 {
    SLIP39_GROUP_COUNT
        .get()
        .unwrap_or(DEFAULT_SLIP39_GROUP_COUNT)
}

#[no_mangle]
pub static mp_module_trezorstoragerecovery: Module = obj_module! {
    Qstr::MP_QSTR___name_recovery__ => Qstr::MP_QSTR_trezorstoragerecovery.to_obj(),

    /// def is_in_progress() -> bool:
    ///     """Whether recovery is in progress."""
    Qstr::MP_QSTR_is_in_progress => obj_fn_0!(is_in_progress).as_obj(),

    /// def set_in_progress(val: bool) -> None:
    ///     """Set in progress."""
    Qstr::MP_QSTR_set_in_progress => obj_fn_1!(set_in_progress).as_obj(),

    /// def is_dry_run() -> bool:
    ///     """Whether recovery is dry - just a test."""
    Qstr::MP_QSTR_is_dry_run => obj_fn_0!(is_dry_run).as_obj(),

    /// def set_dry_run(val: bool) -> None:
    ///     """Set the dry run."""
    Qstr::MP_QSTR_set_dry_run => obj_fn_1!(set_dry_run).as_obj(),

    /// def get_slip39_identifier() -> int | None:
    ///     """Get slip39 identifier."""
    Qstr::MP_QSTR_get_slip39_identifier => obj_fn_0!(get_slip39_identifier).as_obj(),

    /// def set_slip39_identifier(identifier: int) -> None:
    ///     """Set slip39 identifier."""
    Qstr::MP_QSTR_set_slip39_identifier => obj_fn_1!(set_slip39_identifier).as_obj(),

    /// def get_slip39_iteration_exponent() -> int | None:
    ///     """Get slip39 iteration exponent."""
    Qstr::MP_QSTR_get_slip39_iteration_exponent => obj_fn_0!(get_slip39_iteration_exponent).as_obj(),

    /// def set_slip39_iteration_exponent(exponent: int) -> None:
    ///     """Set slip39 iteration exponent."""
    Qstr::MP_QSTR_set_slip39_iteration_exponent => obj_fn_1!(set_slip39_iteration_exponent).as_obj(),

    /// def get_slip39_group_count() -> int:
    ///     """Get slip39 group count."""
    Qstr::MP_QSTR_get_slip39_group_count => obj_fn_0!(get_slip39_group_count).as_obj(),

    /// def set_slip39_group_count(group_count: int) -> None:
    ///     """Set slip39 group count."""
    Qstr::MP_QSTR_set_slip39_group_count => obj_fn_1!(set_slip39_group_count).as_obj(),

    /// def get_slip39_remaining_shares(group_index: int) -> int | None:
    ///     """Get slip39 remaining shares."""
    Qstr::MP_QSTR_get_slip39_remaining_shares => obj_fn_1!(get_slip39_remaining_shares).as_obj(),

    /// def fetch_slip39_remaining_shares() -> list[int] | None:
    ///     """Fetch slip39 remaining shares."""
    Qstr::MP_QSTR_fetch_slip39_remaining_shares => obj_fn_0!(fetch_slip39_remaining_shares).as_obj(),

    /// def set_slip39_remaining_shares(shares_remaining: int, group_index: int) -> None:
    ///     """Set slip39 remaining shares."""
    Qstr::MP_QSTR_set_slip39_remaining_shares => obj_fn_2!(set_slip39_remaining_shares).as_obj(),

    /// def end_progress() -> None:
    ///     """Finish recovery."""
    Qstr::MP_QSTR_end_progress => obj_fn_0!(end_progress).as_obj(),
};
