use crate::{
    error::Error,
    micropython::{
        buffer::{Buffer, StrBuffer},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
    },
    storagedevice::field::Field,
    trezorhal::{random, secbool},
    util,
};

use cstr_core::cstr;
use heapless::{String, Vec};

use core::{
    convert::{TryFrom, TryInto},
    str,
};

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

#[no_mangle]
pub static mp_module_trezorstoragerecovery: Module = obj_module! {
    Qstr::MP_QSTR___name_recovery__ => Qstr::MP_QSTR_trezorstoragerecovery.to_obj(),

    /// def is_in_progress() -> bool:
    ///     """Whether recovery is in progress."""
    Qstr::MP_QSTR_is_in_progress => obj_fn_0!(storagerecovery_is_in_progress).as_obj(),

    /// def set_in_progress(val: bool) -> None:
    ///     """Set in progress."""
    Qstr::MP_QSTR_set_in_progress => obj_fn_1!(storagerecovery_set_in_progress).as_obj(),
};
