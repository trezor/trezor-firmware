#![allow(dead_code)]

use crate::trezorhal::storage::{get, get_length, StorageResult};

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
const HIDE_PASSPHRASE_FROM_HOST: u16 = APP_DEVICE | 0x0016;

pub fn get_avatar_len() -> StorageResult<usize> {
    get_length(HOMESCREEN)
}

pub fn load_avatar(dest: &mut [u8]) -> StorageResult<()> {
    let dest_len = dest.len();
    let result = get(HOMESCREEN, dest)?;
    ensure!(dest_len == result.len(), "Internal error in load_avatar");
    Ok(())
}
