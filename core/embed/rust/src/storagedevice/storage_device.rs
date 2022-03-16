use crate::{
    micropython::{buffer::Buffer, map::Map, module::Module, obj::Obj, qstr::Qstr},
    trezorhal::secbool,
    util,
};

use heapless::Vec;

use core::convert::{TryFrom, TryInto};

// TODO: can we import messages enums?

// MISSING FUNCTIONALITY:
// - returning strings into python
// - raising custom exceptions into python

const FLAG_PUBLIC: u8 = 0x80;

const APP_DEVICE: u8 = 0x01;

// Longest possible entry in storage (homescreen is handled in separate
// function)
const MAX_LEN: usize = 300;

const _FALSE_BYTE: u8 = 0x00;
const _TRUE_BYTE: u8 = 0x01;

const HOMESCREEN_MAXSIZE: usize = 16384;
const LABEL_MAXLENGTH: u16 = 32;

// TODO: transfer this into a struct with field specifying data type and
// `max_length`, possibly even `is_public`
// impl get a impl set
// INITIALIZED: data_type...

const DEVICE_ID: u8 = 0x00;
const _VERSION: u8 = 0x01;
const _MNEMONIC_SECRET: u8 = 0x02;
const _LANGUAGE: u8 = 0x03; // seems it is not used at all
const _LABEL: u8 = 0x04;
const _USE_PASSPHRASE: u8 = 0x05;
const _HOMESCREEN: u8 = 0x06;
const _NEEDS_BACKUP: u8 = 0x07;
const _FLAGS: u8 = 0x08;
const U2F_COUNTER: u8 = 0x09;
const _PASSPHRASE_ALWAYS_ON_DEVICE: u8 = 0x0A;
const _UNFINISHED_BACKUP: u8 = 0x0B;
const _AUTOLOCK_DELAY_MS: u8 = 0x0C;
const _NO_BACKUP: u8 = 0x0D;
const _BACKUP_TYPE: u8 = 0x0E;
const _ROTATION: u8 = 0x0F;
const _SLIP39_IDENTIFIER: u8 = 0x10;
const _SLIP39_ITERATION_EXPONENT: u8 = 0x11;
const _SD_SALT_AUTH_KEY: u8 = 0x12;
const INITIALIZED: u8 = 0x13;
const _SAFETY_CHECK_LEVEL: u8 = 0x14;
const _EXPERIMENTAL_FEATURES: u8 = 0x15;

const SAFETY_CHECK_LEVEL_STRICT: u8 = 0;
const SAFETY_CHECK_LEVEL_PROMPT: u8 = 0;
const _DEFAULT_SAFETY_CHECK_LEVEL: u8 = SAFETY_CHECK_LEVEL_STRICT;
const SAFETY_CHECK_LEVELS: [u8; 2] = [SAFETY_CHECK_LEVEL_STRICT, SAFETY_CHECK_LEVEL_PROMPT];

// TODO: somehow determine the DEBUG_MODE value
const DEBUG_MODE: bool = true;
const AUTOLOCK_DELAY_DEFAULT: u32 = 10 * 60 * 1000; // 10 minutes
const AUTOLOCK_DELAY_MINIMUM: u32 = if DEBUG_MODE {
    10 * 1000 // 10 seconds
} else {
    60 * 1000 // 1 minute
};
// autolock intervals larger than AUTOLOCK_DELAY_MAXIMUM cause issues in the
// scheduler
const AUTOLOCK_DELAY_MAXIMUM: u32 = 0x2000_0000; // ~6 days

// Length of SD salt auth tag.
// Other SD-salt-related constants are in core/src/storage/sd_salt.py
const SD_SALT_AUTH_KEY_LEN_BYTES: u8 = 16;

extern "C" {
    // storage.h
    fn storage_has(key: u16) -> secbool::Secbool;
    fn storage_delete(key: u16) -> secbool::Secbool;
    fn storage_get(
        key: u16,
        // val: *mut cty::c_void,
        val: *const u8,
        max_len: u16,
        len: *mut u16,
    ) -> secbool::Secbool;
    // fn storage_set(key: u16, val: *const cty::c_void, len: u16) ->
    // secbool::Secbool;
    fn storage_set(key: u16, val: *const u8, len: u16) -> secbool::Secbool;

}

extern "C" fn storagedevice_is_version_stored() -> Obj {
    let block = || {
        let key = _get_appkey(_VERSION, false);
        Ok(storagedevice_storage_has(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_version() -> Obj {
    let block = || {
        let key = _get_appkey(_VERSION, false);
        let result = &storagedevice_storage_get(key) as &[u8];
        result.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_version(version: Obj) -> Obj {
    let block = || {
        let version = Buffer::try_from(version)?;
        let len = version.len() as u16;
        let val = version.as_ptr();

        let key = _get_appkey(_VERSION, false);
        Ok(storagedevice_storage_set(key, val, len).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_is_initialized() -> Obj {
    let block = || {
        let key = _get_appkey(INITIALIZED, true);
        Ok(storagedevice_storage_get_bool(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_rotation() -> Obj {
    let block = || {
        let key = _get_appkey(_ROTATION, true);
        Ok(storagedevice_storage_get_u16(key).unwrap_or(0).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_rotation(rotation: Obj) -> Obj {
    let block = || {
        let rotation = u16::try_from(rotation)?;

        // TODO: how to raise a micropython exception?
        if ![0, 90, 180, 270].contains(&rotation) {
            // return Error::ValueError(cstr!("Not valid rotation"));
        }

        let key = _get_appkey(_ROTATION, true);
        Ok(storagedevice_storage_set_u16(key, rotation).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_label() -> Obj {
    let block = || {
        let key = _get_appkey(_LABEL, true);
        let result = &storagedevice_storage_get(key) as &[u8];
        if result.is_empty() {
            //  TODO: it did not work with None::<&[u8]>, but it should not matter
            return Ok(None::<u16>.into());
        }
        // TODO: how to convert into a string?
        // let label = StrBuffer::try_from(*result)?;
        result.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_label(label: Obj) -> Obj {
    let block = || {
        let label = Buffer::try_from(label)?;
        let len = label.len() as u16;

        // TODO: how to raise a micropython exception?
        if len > LABEL_MAXLENGTH {
            return Ok(false.into());
            // return Error::ValueError(cstr!("Label is too long"));
        }

        let val = label.as_ptr();
        let key = _get_appkey(_LABEL, true);
        Ok(storagedevice_storage_set(key, val, len).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_mnemonic_secret() -> Obj {
    let block = || {
        let key = _get_appkey(_MNEMONIC_SECRET, false);
        let result = &storagedevice_storage_get(key) as &[u8];
        result.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_is_passphrase_enabled() -> Obj {
    let block = || {
        let key = _get_appkey(_USE_PASSPHRASE, false);
        Ok(storagedevice_storage_get_bool(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_passphrase_enabled(enable: Obj) -> Obj {
    let block = || {
        let enable = bool::try_from(enable)?;

        let key = _get_appkey(_USE_PASSPHRASE, false);
        let result = storagedevice_storage_set_bool(key, enable);

        if !enable {
            // TODO: could we reuse storagedevice_set_passphrase_always_on_device?
            let key = _get_appkey(_PASSPHRASE_ALWAYS_ON_DEVICE, false);
            storagedevice_storage_set_bool(key, false);
        }

        Ok(result.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_passphrase_always_on_device() -> Obj {
    let block = || {
        let key = _get_appkey(_PASSPHRASE_ALWAYS_ON_DEVICE, false);
        Ok(storagedevice_storage_get_bool(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_passphrase_always_on_device(enable: Obj) -> Obj {
    let block = || {
        let enable = bool::try_from(enable)?;

        let key = _get_appkey(_PASSPHRASE_ALWAYS_ON_DEVICE, false);
        Ok(storagedevice_storage_set_bool(key, enable).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_unfinished_backup() -> Obj {
    let block = || {
        let key = _get_appkey(_UNFINISHED_BACKUP, false);
        Ok(storagedevice_storage_get_bool(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_unfinished_backup(state: Obj) -> Obj {
    let block = || {
        let state = bool::try_from(state)?;

        let key = _get_appkey(_UNFINISHED_BACKUP, false);
        Ok(storagedevice_storage_set_bool(key, state).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_needs_backup() -> Obj {
    let block = || {
        let key = _get_appkey(_NEEDS_BACKUP, false);
        Ok(storagedevice_storage_get_bool(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_backed_up() -> Obj {
    let block = || {
        let key = _get_appkey(_NEEDS_BACKUP, false);
        Ok(storagedevice_storage_delete(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_no_backup() -> Obj {
    let block = || {
        let key = _get_appkey(_NO_BACKUP, false);
        Ok(storagedevice_storage_get_bool(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_homescreen() -> Obj {
    let block = || {
        let key = _get_appkey(_HOMESCREEN, false);
        let result = &storagedevice_storage_get_homescreen(key) as &[u8];
        if result.is_empty() {
            return Ok(None::<u16>.into());
        }
        result.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_homescreen(homescreen: Obj) -> Obj {
    let block = || {
        let homescreen = Buffer::try_from(homescreen)?;
        let len = homescreen.len() as u16;

        // TODO: how to raise a micropython exception?
        if len > HOMESCREEN_MAXSIZE as u16 {
            return Ok(false.into());
            // return Error::ValueError(cstr!("Homescreen too large"));
        }

        let val = homescreen.as_ptr();

        let key = _get_appkey(_HOMESCREEN, false);
        Ok(storagedevice_storage_set(key, val, len).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_slip39_identifier() -> Obj {
    let block = || {
        let key = _get_appkey(_SLIP39_IDENTIFIER, false);
        Ok(storagedevice_storage_get_u16(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_slip39_identifier(identifier: Obj) -> Obj {
    let block = || {
        let identifier = u16::try_from(identifier)?;

        let key = _get_appkey(_SLIP39_IDENTIFIER, false);
        Ok(storagedevice_storage_set_u16(key, identifier).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_slip39_iteration_exponent() -> Obj {
    let block = || {
        let key = _get_appkey(_SLIP39_ITERATION_EXPONENT, false);
        Ok(storagedevice_storage_get_u8(key).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_slip39_iteration_exponent(exponent: Obj) -> Obj {
    let block = || {
        let exponent = u8::try_from(exponent)?;

        let key = _get_appkey(_SLIP39_ITERATION_EXPONENT, false);
        Ok(storagedevice_storage_set_u8(key, exponent).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_autolock_delay_ms() -> Obj {
    let block = || {
        let key = _get_appkey(_AUTOLOCK_DELAY_MS, false);
        match storagedevice_storage_get_u32(key) {
            // TODO: strange that u8 and u16 have .into(), but u32 needs .try_into()
            Some(delay) => _normalize_autolock_delay(delay).try_into(),
            None => AUTOLOCK_DELAY_DEFAULT.try_into(),
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_autolock_delay_ms(delay_ms: Obj) -> Obj {
    let block = || {
        let delay_ms = u32::try_from(delay_ms)?;

        let key = _get_appkey(_AUTOLOCK_DELAY_MS, false);
        Ok(storagedevice_storage_set_u32(key, delay_ms).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_flags() -> Obj {
    let block = || {
        let key = _get_appkey(_FLAGS, false);
        storagedevice_storage_get_u32(key).unwrap_or(0).try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_flags(flags: Obj) -> Obj {
    let block = || {
        let flags = u32::try_from(flags)?;

        let key = _get_appkey(_FLAGS, false);

        let old_flags = storagedevice_storage_get_u32(key).unwrap_or(0);

        // Not deleting old flags
        let new_flags = flags | old_flags;
        Ok(storagedevice_storage_set_u32(key, new_flags).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_safety_check_level() -> Obj {
    let block = || {
        let key = _get_appkey(_SAFETY_CHECK_LEVEL, false);
        let level = storagedevice_storage_get_u8(key).unwrap_or(0);

        let level = if !SAFETY_CHECK_LEVELS.contains(&level) {
            _DEFAULT_SAFETY_CHECK_LEVEL
        } else {
            level
        };

        Ok(level.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_safety_check_level(level: Obj) -> Obj {
    let block = || {
        let level = u8::try_from(level)?;

        // TODO: how to raise a micropython exception?
        if !SAFETY_CHECK_LEVELS.contains(&level) {
            // return Error::ValueError(cstr!("Not valid safety level"));
        }

        let key = _get_appkey(_SAFETY_CHECK_LEVEL, false);
        Ok(storagedevice_storage_set_u8(key, level).into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_get_sd_salt_auth_key() -> Obj {
    let block = || {
        let key = _get_appkey(_SD_SALT_AUTH_KEY, true);
        let result = &storagedevice_storage_get(key) as &[u8];
        if result.is_empty() {
            return Ok(None::<u16>.into());
        } else if result.len() != SD_SALT_AUTH_KEY_LEN_BYTES as usize {
            // TODO: how to raise a micropython exception?
            // return Error::ValueError(cstr!("Invalid key length"));
        }
        result.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn storagedevice_set_sd_salt_auth_key(auth_key: Obj) -> Obj {
    let block = || {
        let auth_key = Buffer::try_from(auth_key)?;

        let key = _get_appkey(_SD_SALT_AUTH_KEY, true);
        if auth_key.is_empty() {
            Ok(storagedevice_storage_delete(key).into())
        } else {
            // TODO: how to raise a micropython exception?
            if auth_key.len() != SD_SALT_AUTH_KEY_LEN_BYTES as usize {
                // return Error::ValueError(cstr!("Invalid key length"));
            }
            Ok(storagedevice_storage_set(key, auth_key.as_ptr(), auth_key.len() as u16).into())
        }
    };
    unsafe { util::try_or_raise(block) }
}

pub fn storagedevice_storage_get(key: u16) -> Vec<u8, MAX_LEN> {
    let mut buf: [u8; MAX_LEN] = [0; MAX_LEN];
    let mut len: u16 = 0;
    // TODO: when the max_len is exceeded, it returns secbool::FALSE - we should
    // catch it
    unsafe { storage_get(key, &mut buf as *mut _, MAX_LEN as u16, &mut len as *mut _) };
    // TODO: when the result is empty, we could return None
    // Would mean having Option<XXX> as the return type

    let result = &buf[..len as usize];
    // TODO: can we somehow convert it more easily?
    let mut vector_result = Vec::<u8, MAX_LEN>::new();
    for byte in result {
        vector_result.push(*byte).unwrap();
    }

    vector_result
}

// TODO: is it worth having a special function to not allocate so much in all
// other cases?
// TODO: cannot we somehow use the above storagedevice_storage_get?
pub fn storagedevice_storage_get_homescreen(key: u16) -> Vec<u8, HOMESCREEN_MAXSIZE> {
    let mut buf: [u8; HOMESCREEN_MAXSIZE] = [0; HOMESCREEN_MAXSIZE];
    let mut len: u16 = 0;
    unsafe {
        storage_get(
            key,
            &mut buf as *mut _,
            HOMESCREEN_MAXSIZE as u16,
            &mut len as *mut _,
        )
    };

    let result = &buf[..len as usize];
    let mut vector_result = Vec::<u8, HOMESCREEN_MAXSIZE>::new();
    for byte in result {
        vector_result.push(*byte).unwrap();
    }

    vector_result
}

pub fn storagedevice_storage_get_bool(key: u16) -> bool {
    let result = storagedevice_storage_get(key);
    result.len() == 1 && result[0] == _TRUE_BYTE
}

// TODO: can we somehow generalize this for all uint types?
pub fn storagedevice_storage_get_u32(key: u16) -> Option<u32> {
    let result = storagedevice_storage_get(key);
    if result.len() == 4 {
        Some(u32::from_be_bytes([
            result[0], result[1], result[2], result[3],
        ]))
    } else {
        None
    }
}

pub fn storagedevice_storage_get_u16(key: u16) -> Option<u16> {
    let result = storagedevice_storage_get(key);
    if result.len() == 2 {
        Some(u16::from_be_bytes([result[0], result[1]]))
    } else {
        None
    }
}

pub fn storagedevice_storage_get_u8(key: u16) -> Option<u8> {
    let result = storagedevice_storage_get(key);
    if result.len() == 1 {
        Some(u8::from_be_bytes([result[0]]))
    } else {
        None
    }
}

pub fn storagedevice_storage_set(key: u16, val: *const u8, len: u16) -> bool {
    matches!(unsafe { storage_set(key, val, len) }, secbool::TRUE)
}

pub fn storagedevice_storage_set_bool(key: u16, val: bool) -> bool {
    let val = if val { [_TRUE_BYTE] } else { [_FALSE_BYTE] };
    storagedevice_storage_set(key, &val as *const _, 1)
}

pub fn storagedevice_storage_set_u8(key: u16, val: u8) -> bool {
    storagedevice_storage_set(key, &val.to_be_bytes() as *const _, 1)
}

pub fn storagedevice_storage_set_u16(key: u16, val: u16) -> bool {
    storagedevice_storage_set(key, &val.to_be_bytes() as *const _, 2)
}

pub fn storagedevice_storage_set_u32(key: u16, val: u32) -> bool {
    storagedevice_storage_set(key, &val.to_be_bytes() as *const _, 4)
}

pub fn storagedevice_storage_has(key: u16) -> bool {
    matches!(unsafe { storage_has(key) }, secbool::TRUE)
}

pub fn storagedevice_storage_delete(key: u16) -> bool {
    matches!(unsafe { storage_delete(key) }, secbool::TRUE)
}

// TODO: we could include `is_public` bool into each key's struct item

fn _get_appkey(key: u8, is_public: bool) -> u16 {
    let app = if is_public {
        APP_DEVICE | FLAG_PUBLIC
    } else {
        APP_DEVICE
    };
    ((app as u16) << 8) | key as u16
}

fn _normalize_autolock_delay(delay_ms: u32) -> u32 {
    if delay_ms < AUTOLOCK_DELAY_MINIMUM {
        AUTOLOCK_DELAY_MINIMUM
    } else if delay_ms > AUTOLOCK_DELAY_MAXIMUM {
        AUTOLOCK_DELAY_MAXIMUM
    } else {
        delay_ms
    }
}

#[no_mangle]
pub static mp_module_trezorstoragedevice: Module = obj_module! {
    Qstr::MP_QSTR___name_storage__ => Qstr::MP_QSTR_trezorstoragedevice.to_obj(),

    // TODO: should we return None or True in case of set_xxx?

    /// StorageSafetyCheckLevel = Literal[0, 1]

    /// def is_version_stored() -> bool:
    ///     """Whether version is in storage."""
    Qstr::MP_QSTR_is_version_stored => obj_fn_0!(storagedevice_is_version_stored).as_obj(),

    /// def is_initialized() -> bool:
    ///     """Whether device is initialized."""
    Qstr::MP_QSTR_is_initialized => obj_fn_0!(storagedevice_is_initialized).as_obj(),

    /// def get_version() -> bytes:
    ///     """Get version."""
    Qstr::MP_QSTR_get_version => obj_fn_0!(storagedevice_get_version).as_obj(),

    /// def set_version(version: bytes) -> bool:
    ///     """Set version."""
    Qstr::MP_QSTR_set_version => obj_fn_1!(storagedevice_set_version).as_obj(),

    /// def get_rotation() -> int:
    ///     """Get rotation."""
    Qstr::MP_QSTR_get_rotation => obj_fn_0!(storagedevice_get_rotation).as_obj(),

    /// def set_rotation(rotation: int) -> bool:
    ///     """Set rotation."""
    Qstr::MP_QSTR_set_rotation => obj_fn_1!(storagedevice_set_rotation).as_obj(),

    /// def get_label() -> str | None:
    ///     """Get label."""
    Qstr::MP_QSTR_get_label => obj_fn_0!(storagedevice_get_label).as_obj(),

    /// def set_label(label: str) -> bool:
    ///     """Set label."""
    Qstr::MP_QSTR_set_label => obj_fn_1!(storagedevice_set_label).as_obj(),

    /// def get_mnemonic_secret() -> bytes:
    ///     """Get mnemonic secret."""
    Qstr::MP_QSTR_get_mnemonic_secret => obj_fn_0!(storagedevice_get_mnemonic_secret).as_obj(),

    /// def is_passphrase_enabled() -> bool:
    ///     """Whether passphrase is enabled."""
    Qstr::MP_QSTR_is_passphrase_enabled => obj_fn_0!(storagedevice_is_passphrase_enabled).as_obj(),

    /// def set_passphrase_enabled(enable: bool) -> bool:
    ///     """Set whether passphrase is enabled."""
    Qstr::MP_QSTR_set_passphrase_enabled => obj_fn_1!(storagedevice_set_passphrase_enabled).as_obj(),

    /// def get_passphrase_always_on_device() -> bool:
    ///     """Whether passphrase is on device."""
    Qstr::MP_QSTR_get_passphrase_always_on_device => obj_fn_0!(storagedevice_get_passphrase_always_on_device).as_obj(),

    /// def set_passphrase_always_on_device(enable: bool) -> bool:
    ///     """Set whether passphrase is on device.
    ///
    ///     This is backwards compatible with _PASSPHRASE_SOURCE:
    ///     - If ASK(0) => returns False, the check against b"\x01" in get_bool fails.
    ///     - If DEVICE(1) => returns True, the check against b"\x01" in get_bool succeeds.
    ///     - If HOST(2) => returns False, the check against b"\x01" in get_bool fails.
    ///     """
    Qstr::MP_QSTR_set_passphrase_always_on_device => obj_fn_1!(storagedevice_set_passphrase_always_on_device).as_obj(),

    /// def unfinished_backup() -> bool:
    ///     """Whether backup is still in progress."""
    Qstr::MP_QSTR_unfinished_backup => obj_fn_0!(storagedevice_unfinished_backup).as_obj(),

    /// def set_unfinished_backup(state: bool) -> bool:
    ///     """Set backup state."""
    Qstr::MP_QSTR_set_unfinished_backup => obj_fn_1!(storagedevice_set_unfinished_backup).as_obj(),

    /// def needs_backup() -> bool:
    ///     """Whether backup is needed."""
    Qstr::MP_QSTR_needs_backup => obj_fn_0!(storagedevice_needs_backup).as_obj(),

    /// def set_backed_up() -> bool:
    ///     """Signal that backup is finished."""
    Qstr::MP_QSTR_set_backed_up => obj_fn_0!(storagedevice_set_backed_up).as_obj(),

    /// def no_backup() -> bool:
    ///     """Whether there is no backup."""
    Qstr::MP_QSTR_no_backup => obj_fn_0!(storagedevice_no_backup).as_obj(),

    /// def get_homescreen() -> bytes | None:
    ///     """Get homescreen."""
    Qstr::MP_QSTR_get_homescreen => obj_fn_0!(storagedevice_get_homescreen).as_obj(),

    /// def set_homescreen(homescreen: bytes) -> bool:
    ///     """Set homescreen."""
    Qstr::MP_QSTR_set_homescreen => obj_fn_1!(storagedevice_set_homescreen).as_obj(),

    /// def get_slip39_identifier() -> int | None:
    ///     """The device's actual SLIP-39 identifier used in passphrase derivation."""
    Qstr::MP_QSTR_get_slip39_identifier => obj_fn_0!(storagedevice_get_slip39_identifier).as_obj(),

    /// def set_slip39_identifier(identifier: int) -> bool:
    ///     """
    ///     The device's actual SLIP-39 identifier used in passphrase derivation.
    ///     Not to be confused with recovery.identifier, which is stored only during
    ///     the recovery process and it is copied here upon success.
    ///     """
    Qstr::MP_QSTR_set_slip39_identifier => obj_fn_1!(storagedevice_set_slip39_identifier).as_obj(),

    /// def get_slip39_iteration_exponent() -> int | None:
    ///     """The device's actual SLIP-39 iteration exponent used in passphrase derivation."""
    Qstr::MP_QSTR_get_slip39_iteration_exponent => obj_fn_0!(storagedevice_get_slip39_iteration_exponent).as_obj(),

    /// def set_slip39_iteration_exponent(exponent: int) -> bool:
    ///     """
    ///     The device's actual SLIP-39 iteration exponent used in passphrase derivation.
    ///     Not to be confused with recovery.iteration_exponent, which is stored only during
    ///     the recovery process and it is copied here upon success.
    ///     """
    Qstr::MP_QSTR_set_slip39_iteration_exponent => obj_fn_1!(storagedevice_set_slip39_iteration_exponent).as_obj(),

    /// def get_autolock_delay_ms() -> int:
    ///     """Get autolock delay."""
    Qstr::MP_QSTR_get_autolock_delay_ms => obj_fn_0!(storagedevice_get_autolock_delay_ms).as_obj(),

    /// def set_autolock_delay_ms(delay_ms: int) -> bool:
    ///     """Set autolock delay."""
    Qstr::MP_QSTR_set_autolock_delay_ms => obj_fn_1!(storagedevice_set_autolock_delay_ms).as_obj(),

    /// def get_flags() -> int:
    ///     """Get flags."""
    Qstr::MP_QSTR_get_flags => obj_fn_0!(storagedevice_get_flags).as_obj(),

    /// def set_flags(flags: int) -> bool:
    ///     """Set flags."""
    Qstr::MP_QSTR_set_flags => obj_fn_1!(storagedevice_set_flags).as_obj(),

    /// def get_safety_check_level() -> StorageSafetyCheckLevel:
    ///     """Get safety check level.
    ///     Do not use this function directly, see apps.common.safety_checks instead.
    ///     """
    Qstr::MP_QSTR_get_safety_check_level => obj_fn_0!(storagedevice_get_safety_check_level).as_obj(),

    /// def set_safety_check_level(level: StorageSafetyCheckLevel) -> bool:
    ///     """Set safety check level.
    ///     Do not use this function directly, see apps.common.safety_checks instead.
    ///     """
    Qstr::MP_QSTR_set_safety_check_level => obj_fn_1!(storagedevice_set_safety_check_level).as_obj(),

    /// def get_sd_salt_auth_key() -> bytes | None:
    ///     """The key used to check the authenticity of the SD card salt."""
    Qstr::MP_QSTR_get_sd_salt_auth_key => obj_fn_0!(storagedevice_get_sd_salt_auth_key).as_obj(),

    /// def set_sd_salt_auth_key(auth_key: bytes | None) -> bool:
    ///     """The key used to check the authenticity of the SD card salt."""
    Qstr::MP_QSTR_set_sd_salt_auth_key => obj_fn_1!(storagedevice_set_sd_salt_auth_key).as_obj(),
};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_appkey() {
        let result = _get_appkey(0x11, false);
        assert_eq!(result, 0x0111);
    }

    #[test]
    fn get_appkey_public() {
        let result = _get_appkey(0x11, true);
        assert_eq!(result, 0x8111);
    }

    #[test]
    fn normalize_autolock_delay_small() {
        let result = _normalize_autolock_delay(123);
        assert_eq!(result, AUTOLOCK_DELAY_MINIMUM);
    }

    #[test]
    fn normalize_autolock_delay_big() {
        let result = _normalize_autolock_delay(u32::MAX);
        assert_eq!(result, AUTOLOCK_DELAY_MAXIMUM);
    }

    #[test]
    fn normalize_autolock_delay_normal() {
        let result = _normalize_autolock_delay(1_000_000);
        assert_eq!(result, 1_000_000);
    }
}
