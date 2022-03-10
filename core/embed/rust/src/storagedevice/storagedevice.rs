use crate::{
    micropython::{buffer::Buffer, obj::Obj},
    trezorhal::secbool,
    util,
};

use core::convert::{TryFrom, TryInto};

// TODO: transfer this into a struct with field specifying data type and
// max_length
const APP_DEVICE: u16 = 0x01;

const DEVICE_ID: u16 = 0x01;
const _VERSION: u16 = 0x02;
const _MNEMONIC_SECRET: u16 = 0x03;
const _LANGUAGE: u16 = 0x04;
const _LABEL: u16 = 0x05;
const _USE_PASSPHRASE: u16 = 0x06;
const _HOMESCREEN: u16 = 0x07;
const _NEEDS_BACKUP: u16 = 0x08;
const _FLAGS: u16 = 0x09;
const U2F_COUNTER: u16 = 0x0A;
const _PASSPHRASE_ALWAYS_ON_DEVICE: u16 = 0x0B;
const _UNFINISHED_BACKUP: u16 = 0x0C;
const _AUTOLOCK_DELAY_MS: u16 = 0x0D;
const _NO_BACKUP: u16 = 0x0E;
const _BACKUP_TYPE: u16 = 0x0F;
const _ROTATION: u16 = 0x10;
const _SLIP39_IDENTIFIER: u16 = 0x11;
const _SLIP39_ITERATION_EXPONENT: u16 = 0x12;
const _SD_SALT_AUTH_KEY: u16 = 0x13;
const INITIALIZED: u16 = 0x14;
const _SAFETY_CHECK_LEVEL: u16 = 0x15;
const _EXPERIMENTAL_FEATURES: u16 = 0x16;

extern "C" {
    // storage.h
    fn storage_has(key: u16) -> secbool::Secbool;
    fn storage_delete(key: u16) -> secbool::Secbool;
    fn storage_get(
        key: u16,
        // val: *mut cty::c_void,
        // val: *mut BufferMut,
        val: *mut u8,
        max_len: u16,
        len: *mut u16,
    ) -> secbool::Secbool;
    // fn storage_set(key: u16, val: *const cty::c_void, len: u16) ->
    // secbool::Secbool;
    fn storage_set(key: u16, val: Buffer, len: u16) -> secbool::Secbool;
}

#[no_mangle]
pub extern "C" fn storagedevice_is_version_stored() -> Obj {
    let block = || {
        let key: u16 = 0x0102;
        let result = storagedevice_storage_has(key);
        Ok(result.into())
    };
    unsafe { util::try_or_raise(block) }
}

// #[no_mangle]
// pub extern "C" fn storagedevice_get_version() -> Obj {
//     let block = || {
//         let key: u16 = 0x0102;
//         let result = storagedevice_storage_get(key);
//         Ok(result.into())
//     };
//     unsafe { util::try_or_raise(block) }
// }

#[no_mangle]
pub extern "C" fn storagedevice_set_version(version: Obj) -> Obj {
    let block = || {
        let value = Buffer::try_from(version)?;

        let key: u16 = 0x0102;
        let result = storagedevice_storage_set(key, value);
        Ok(result.into())
    };
    unsafe { util::try_or_raise(block) }
}

// pub fn storagedevice_storage_get(key: u16) -> BufferMut {
//     const MAX_LEN: usize = 300;
//     // let mut buf: [u8; MAX_LEN] = [0; MAX_LEN];
//     let mut buf: BufferMut;
//     let mut len: u16 = 0;
//     unsafe { storage_get(key, &mut buf as *mut _, MAX_LEN as u16, &mut len as
// *mut _) };     buf[..len as usize] as BufferMut
// }

pub fn storagedevice_storage_set(key: u16, value: Buffer) -> bool {
    let len = value.len();
    match unsafe { storage_set(key, value, len as u16) } {
        secbool::TRUE => true,
        _ => false,
    }
}

pub fn storagedevice_storage_has(key: u16) -> bool {
    match unsafe { storage_has(key) } {
        secbool::TRUE => true,
        _ => false,
    }
}

pub fn storagedevice_storage_delete(key: u16) -> bool {
    match unsafe { storage_delete(key) } {
        secbool::TRUE => true,
        _ => false,
    }
}
