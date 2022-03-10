use crate::{
    micropython::{buffer::Buffer, obj::Obj},
    trezorhal::secbool,
    util,
};

use core::convert::{TryFrom, TryInto};

// TODO: transfer this into a struct with field specifying data type and
// max_length
const APP_DEVICE: u8 = 0x01;

const DEVICE_ID: u8 = 0x01;
const _VERSION: u8 = 0x02;
const _MNEMONIC_SECRET: u8 = 0x03;
const _LANGUAGE: u8 = 0x04;
const _LABEL: u8 = 0x05;
const _USE_PASSPHRASE: u8 = 0x06;
const _HOMESCREEN: u8 = 0x07;
const _NEEDS_BACKUP: u8 = 0x08;
const _FLAGS: u8 = 0x09;
const U2F_COUNTER: u8 = 0x0A;
const _PASSPHRASE_ALWAYS_ON_DEVICE: u8 = 0x0B;
const _UNFINISHED_BACKUP: u8 = 0x0C;
const _AUTOLOCK_DELAY_MS: u8 = 0x0D;
const _NO_BACKUP: u8 = 0x0E;
const _BACKUP_TYPE: u8 = 0x0F;
const _ROTATION: u8 = 0x10;
const _SLIP39_IDENTIFIER: u8 = 0x11;
const _SLIP39_ITERATION_EXPONENT: u8 = 0x12;
const _SD_SALT_AUTH_KEY: u8 = 0x13;
const INITIALIZED: u8 = 0x14;
const _SAFETY_CHECK_LEVEL: u8 = 0x15;
const _EXPERIMENTAL_FEATURES: u8 = 0x16;

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
        let key = _get_appkey(_VERSION);
        let result = storagedevice_storage_has(key);
        Ok(result.into())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn storagedevice_get_version() -> Obj {
    let block = || {
        let key = _get_appkey(_VERSION);
        let (buf, len) = storagedevice_storage_get(key);
        let result = &buf[..len as usize];
        // let result = storagedevice_storage_get(key);
        result.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn storagedevice_set_version(version: Obj) -> Obj {
    let block = || {
        let value = Buffer::try_from(version)?;

        let key = _get_appkey(_VERSION);
        let result = storagedevice_storage_set(key, value);
        Ok(result.into())
    };
    unsafe { util::try_or_raise(block) }
}

// TODO: find out how to return the real result
// pub fn storagedevice_storage_get(key: u16) -> &'static [u8] {
// pub fn storagedevice_storage_get(key: u16) -> [u8] {
pub fn storagedevice_storage_get(key: u16) -> ([u8; 300], u16) {
    const MAX_LEN: usize = 300;
    let mut buf: [u8; MAX_LEN] = [0; MAX_LEN];
    // let mut buf: BufferMut;
    let mut len: u16 = 0;
    unsafe { storage_get(key, &mut buf as *mut _, MAX_LEN as u16, &mut len as *mut _) };
    // TODO: when the result is empty, we could return None
    // Would mean having Option<XXX> as the return type

    // &buf[..len as usize]
    // buf[..len as usize]
    (buf, len)
}

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

fn _get_appkey(key: u8) -> u16 {
    ((APP_DEVICE as u16) << 8) | key as u16
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_appkey() {
        let result = _get_appkey(0x11);
        assert_eq!(result, 0x0111);
    }
}
