#![allow(dead_code)]

use crate::trezorhal::{
    random,
    storage::{delete, get, get_length, set, set_counter, StorageResult},
};
use cstr_core::CStr;
use heapless::{String, Vec};

pub const HOMESCREEN_MAX_SIZE: usize = 16384;

const STORAGE_VERSION_01: u8 = 1;
const STORAGE_VERSION_02: u8 = 2;
const STORAGE_VERSION_CURRENT: u8 = STORAGE_VERSION_02;

const FLAG_PUBLIC: u16 = 0x8000;
const FLAG_WRITE: u16 = 0xC000;
const APP_DEVICE: u16 = 0x0100;

const DEVICE_ID: u16 = FLAG_PUBLIC | APP_DEVICE;
const VERSION: u16 = APP_DEVICE | 0x0001;
const MNEMONIC_SECRET: u16 = APP_DEVICE | 0x0002;
// NOTE: 0x03 key was used in the past for LANGUAGE. Not used anymore.
const LABEL: u16 = FLAG_PUBLIC | APP_DEVICE | 0x0004;
const USE_PASSPHRASE: u16 = APP_DEVICE | 0x0005;
const HOMESCREEN: u16 = FLAG_PUBLIC | APP_DEVICE | 0x0006;
const NEEDS_BACKUP: u16 = APP_DEVICE | 0x0007;
const FLAGS: u16 = APP_DEVICE | 0x0008;
const U2F_COUNTER_PRIVATE: u16 = APP_DEVICE | 0x0009;
const U2F_COUNTER: u16 = FLAG_PUBLIC | APP_DEVICE | 0x0009;
const PASSPHRASE_ALWAYS_ON_DEVICE: u16 = APP_DEVICE | 0x000A;
const UNFINISHED_BACKUP: u16 = APP_DEVICE | 0x000B;
const AUTOLOCK_DELAY_MS: u16 = APP_DEVICE | 0x000C;
const NO_BACKUP: u16 = APP_DEVICE | 0x000D;
const BACKUP_TYPE: u16 = APP_DEVICE | 0x000E;
const ROTATION: u16 = FLAG_PUBLIC | APP_DEVICE | 0x000F;
const SLIP39_IDENTIFIER: u16 = APP_DEVICE | 0x0010;
const SLIP39_ITERATION_EXPONENT: u16 = APP_DEVICE | 0x0011;
const SD_SALT_AUTH_KEY: u16 = FLAG_PUBLIC | APP_DEVICE | 0x0012;
const INITIALIZED: u16 = FLAG_PUBLIC | APP_DEVICE | 0x0013;
const SAFETY_CHECK_LEVEL: u16 = APP_DEVICE | 0x0014;
const EXPERIMENTAL_FEATURES: u16 = APP_DEVICE | 0x0015;

pub fn get_avatar_len() -> StorageResult<usize> {
    get_length(HOMESCREEN)
}

pub fn load_avatar(dest: &mut [u8]) -> StorageResult<()> {
    let dest_len = dest.len();
    let result = get(HOMESCREEN, dest)?;
    ensure!(dest_len == result.len(), "Internal error in load_avatar");
    Ok(())
}

pub fn hexlify_bytes<const N: usize>(bytes: &[u8]) -> String<N> {
    let mut buf = String::<N>::from("");
    for byte in bytes {
        fn hex_from_digit(num: u8) -> char {
            if num < 10 {
                (b'0' + num) as char
            } else {
                (b'A' + num - 10) as char
            }
        }
        buf.push(hex_from_digit(byte / 16)).unwrap();
        buf.push(hex_from_digit(byte % 16)).unwrap();
    }
    buf
}

pub fn get_device_id() -> String<24> {
    let mut buf: [u8; 25] = [0_u8; 25];

    let res = get(DEVICE_ID, &mut buf);

    if res.is_err() {
        random::bytes(&mut buf);
        let hex_id: String<24> = hexlify_bytes(&buf[..24]);
        unwrap!(set(DEVICE_ID, hex_id.as_bytes()), "cannot set device ID");
        hex_id
    } else {
        let text = unsafe { CStr::from_bytes_with_nul_unchecked(&buf).to_str().unwrap() };
        String::from(text)
    }
}

pub fn get_flag(key: u16) -> bool {
    let mut buf = [0u8];
    let result = get(key, &mut buf);
    if let Ok(result) = result {
        result[0] != 0
    } else {
        false
    }
}

pub fn migrate_from_version_01() {
    // Make the U2F counter public and writable even when storage is locked.
    // U2F counter wasn't public, so we are intentionally not using storage.device
    // module.
    let mut data: [u8; 4] = [0; 4];
    let counter_res = get(U2F_COUNTER_PRIVATE, &mut data);
    if counter_res.is_ok() {
        let counter = u32::from_be_bytes(data);

        unwrap!(set_counter(FLAG_WRITE | U2F_COUNTER, counter));
        // Delete the old, non-public U2F_COUNTER.
        unwrap!(delete(U2F_COUNTER_PRIVATE));
    }
    unwrap!(set(VERSION, &[STORAGE_VERSION_CURRENT; 1]));
}

pub fn init_unlocked() {
    let len_res = get_length(VERSION);

    if len_res.is_ok() {
        // Check for storage version upgrade.
        let mut data: [u8; 1] = [0; 1];
        unwrap!(get(VERSION, &mut data));

        if data[0] == STORAGE_VERSION_01 {
            migrate_from_version_01();
        }

        // In FWs <= 2.3.1 'version' denoted whether the device is initialized or not.
        // In 2.3.2 we have introduced a new field 'initialized' for that.
        if get_flag(VERSION) && !get_flag(INITIALIZED) {
            unwrap!(set(INITIALIZED, &[1; 1]));
        }
    }
}

pub fn get_rotation() -> u16 {
    let rotation_len_res = get_length(ROTATION);
    let rotation: u16 = if rotation_len_res.is_ok() {
        let mut data = [0; 2];
        get(ROTATION, &mut data).unwrap();
        u16::from_be_bytes(data)
    } else {
        0
    };
    rotation
}

pub fn get_device_name() -> String<16> {
    let device_name_len_res = get_length(LABEL);

    let device_name: String<16> = if let Ok(len) = device_name_len_res {
        let mut data: [u8; 17] = [0; 17];
        get(LABEL, &mut data).unwrap();
        let text = unsafe {
            CStr::from_bytes_with_nul_unchecked(&data[..=len])
                .to_str()
                .unwrap()
        };
        String::from(text)
    } else {
        String::from("My Trezor")
    };
    device_name
}

pub fn get_sd_salt_auth_key() -> Option<Vec<u8, 16>> {
    let sd_salt_res = get_length(SD_SALT_AUTH_KEY);
    let sd_salt_auth_key: Option<Vec<u8, 16>> = if sd_salt_res.is_ok() {
        let mut data = [0; 16];
        get(SD_SALT_AUTH_KEY, &mut data).unwrap();
        Some(unwrap!(Vec::from_slice(&data)))
    } else {
        None
    };
    sd_salt_auth_key
}
