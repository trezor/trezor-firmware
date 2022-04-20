use crate::{
    error::Error,
    micropython::{buffer::StrBuffer, map::Map, module::Module, obj::Obj, qstr::Qstr},
    trezorhal::storage_field::{Field, FieldGetSet, FieldOpsBase},
    util,
};
use heapless::{String, Vec};

const APP_RECOVERY_SHARES: u8 = 0x03;

const MAX_SHARE_COUNT: usize = 16;
const MAX_GROUP_COUNT: usize = 16;

extern "C" fn get(index: Obj, group_index: Obj) -> Obj {
    let block = || {
        get_share_string(index.try_into()?, group_index.try_into()?)?
            .as_str()
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set(index: Obj, group_index: Obj, mnemonic: Obj) -> Obj {
    let block = || {
        let index: u8 = index.try_into()?;
        let group_index: u8 = group_index.try_into()?;
        let mnemonic: StrBuffer = mnemonic.try_into()?;

        Field::<String<256>>::private(
            APP_RECOVERY_SHARES,
            index + group_index * MAX_SHARE_COUNT as u8,
        )
        .set(mnemonic.try_into()?)?
        .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn fetch_group(group_index: Obj) -> Obj {
    let block = || {
        let mut result: Vec<String<256>, MAX_SHARE_COUNT> = Vec::new();
        for index in 0..MAX_SHARE_COUNT {
            let share = get_share_string(index as u8, group_index.try_into()?)?;
            if !share.is_empty() {
                result.push(share).unwrap();
            }
        }
        result.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn delete() -> Obj {
    let block = || delete_all_recovery_shares()?.try_into();
    unsafe { util::try_or_raise(block) }
}

pub fn get_share_string(index: u8, group_index: u8) -> Result<String<256>, Error> {
    Ok(Field::<String<256>>::private(
        APP_RECOVERY_SHARES,
        index + group_index * MAX_SHARE_COUNT as u8,
    )
    .get()
    .unwrap_or_else(|| String::from("")))
}

pub fn delete_all_recovery_shares() -> Result<(), Error> {
    for index in 0..MAX_SHARE_COUNT * MAX_GROUP_COUNT {
        Field::<String<256>>::private(APP_RECOVERY_SHARES, index as u8).delete()?;
    }
    Ok(())
}

#[no_mangle]
pub static mp_module_trezorstoragerecoveryshares: Module = obj_module! {
    Qstr::MP_QSTR___name_recoveryshares__ => Qstr::MP_QSTR_trezorstoragerecoveryshares.to_obj(),

    /// def get(index: int, group_index: int) -> str | None:
    ///     """Get recovery share."""
    Qstr::MP_QSTR_get => obj_fn_2!(get).as_obj(),

    /// def set(index: int, group_index: int, mnemonic: str) -> None:
    ///     """Set recovery share."""
    Qstr::MP_QSTR_set => obj_fn_3!(set).as_obj(),

    /// def fetch_group(group_index: int) -> list[str]:
    ///     """Fetch recovery share group."""
    Qstr::MP_QSTR_fetch_group => obj_fn_1!(fetch_group).as_obj(),

    /// def delete() -> None:
    ///     """Delete all recovery shares."""
    Qstr::MP_QSTR_delete => obj_fn_0!(delete).as_obj(),
};
