use crate::{
    error::Error,
    micropython::{
        buffer::{Buffer, StrBuffer},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
    },
    storagedevice::helpers,
    trezorhal::{
        random,
        storage_field::{set_true_or_delete, Counter, Field, FieldGetSet, FieldOpsBase},
    },
    util,
};
use core::convert::{TryFrom, TryInto};
use cstr_core::cstr;
use heapless::{String, Vec};

// TODO: can we import messages enums?

const APP_DEVICE: u8 = 0x01;

const HOMESCREEN_MAXSIZE: usize = 16384;
const LABEL_MAXLENGTH: usize = 32;

// Length of SD salt auth tag.
// Other SD-salt-related constants are in core/src/storage/sd_salt.py
const SD_SALT_AUTH_KEY_LEN_BYTES: usize = 16;

// TODO: how to export all public constants as integers?

const DEVICE_ID: Field<String<24>> = Field::public(APP_DEVICE, 0x00).exact();
const VERSION: Field<u8> = Field::private(APP_DEVICE, 0x01);
const MNEMONIC_SECRET: Field<Vec<u8, 256>> = Field::private(APP_DEVICE, 0x02);
// NOTE: 0x03 key was used in the past for LANGUAGE. Not used anymore.
const LABEL: Field<String<LABEL_MAXLENGTH>> = Field::public(APP_DEVICE, 0x04);
const USE_PASSPHRASE: Field<bool> = Field::private(APP_DEVICE, 0x05);
const HOMESCREEN: Field<Vec<u8, HOMESCREEN_MAXSIZE>> = Field::public(APP_DEVICE, 0x06);
const NEEDS_BACKUP: Field<bool> = Field::private(APP_DEVICE, 0x07);
const FLAGS: Field<u32> = Field::private(APP_DEVICE, 0x08);
const U2F_COUNTER_PRIVATE: Field<u8> = Field::private(APP_DEVICE, 0x09);
const U2F_COUNTER: u8 = 0x09;
const PASSPHRASE_ALWAYS_ON_DEVICE: Field<bool> = Field::private(APP_DEVICE, 0x0A);
const UNFINISHED_BACKUP: Field<bool> = Field::private(APP_DEVICE, 0x0B);
const AUTOLOCK_DELAY_MS: Field<u32> = Field::private(APP_DEVICE, 0x0C);
const NO_BACKUP: Field<bool> = Field::private(APP_DEVICE, 0x0D);
const BACKUP_TYPE: Field<u8> = Field::private(APP_DEVICE, 0x0E);
const ROTATION: Field<u16> = Field::public(APP_DEVICE, 0x0F);
const SLIP39_IDENTIFIER: Field<u16> = Field::private(APP_DEVICE, 0x10);
const SLIP39_ITERATION_EXPONENT: Field<u8> = Field::private(APP_DEVICE, 0x11);
const SD_SALT_AUTH_KEY: Field<Vec<u8, SD_SALT_AUTH_KEY_LEN_BYTES>> =
    Field::public(APP_DEVICE, 0x12).exact();
const INITIALIZED: Field<bool> = Field::public(APP_DEVICE, 0x13);
const SAFETY_CHECK_LEVEL: Field<u8> = Field::private(APP_DEVICE, 0x14);
const EXPERIMENTAL_FEATURES: Field<bool> = Field::private(APP_DEVICE, 0x15);

#[repr(u8)]
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub enum SafetyCheckLevel {
    Strict = 0,
    Prompt = 1,
}

const DEFAULT_SAFETY_CHECK_LEVEL: u8 = SafetyCheckLevel::Strict as u8;

// It is not possible to iterate through all enum variants, so we need to
// hardcode it
// https://stackoverflow.com/questions/21371534/in-rust-is-there-a-way-to-iterate-through-the-values-of-an-enum
const SAFETY_CHECK_LEVELS: [u8; 2] = [
    SafetyCheckLevel::Strict as u8,
    SafetyCheckLevel::Prompt as u8,
];

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

const STORAGE_VERSION_CURRENT: u8 = 0x02;

extern "C" fn is_version_stored() -> Obj {
    VERSION.is_set().into()
}

extern "C" fn get_version() -> Obj {
    VERSION.get().into()
}

extern "C" fn set_version(version: Obj) -> Obj {
    let block = || VERSION.set(version.try_into()?)?.try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn is_initialized() -> Obj {
    INITIALIZED.is_set().into()
}

extern "C" fn set_is_initialized(is_initialized: Obj) -> Obj {
    let block = || INITIALIZED.set(is_initialized.try_into()?)?.try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_rotation() -> Obj {
    ROTATION.get().unwrap_or(0).into()
}

extern "C" fn set_rotation(rotation: Obj) -> Obj {
    let block = || {
        let rotation = rotation.try_into()?;

        if ![0, 90, 180, 270].contains(&rotation) {
            Err(Error::ValueError(cstr!("Not valid rotation")))
        } else {
            ROTATION.set(rotation)?.try_into()
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_label() -> Obj {
    let block = || LABEL.get().try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_label(label: Obj) -> Obj {
    let block = || {
        let label: StrBuffer = label.try_into()?;
        LABEL.set(label.try_into()?)?.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_device_id() -> Obj {
    let block = || {
        if let Some(device_id) = DEVICE_ID.get() {
            device_id.try_into()
        } else {
            let mut buf: [u8; 12] = [0; 12];
            random::bytes(&mut buf);
            let hex_id = helpers::hexlify_bytes(&buf);
            DEVICE_ID.set(hex_id.clone())?;
            hex_id.try_into()
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_device_id(device_id: Obj) -> Obj {
    let block = || {
        let device_id: StrBuffer = device_id.try_into()?;
        DEVICE_ID.set(device_id.try_into()?)?.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_mnemonic_secret() -> Obj {
    let block = || MNEMONIC_SECRET.get().try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_mnemonic_secret(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let secret: Buffer = kwargs.get(Qstr::MP_QSTR_secret)?.try_into()?;
        let backup_type: u8 = kwargs.get(Qstr::MP_QSTR_backup_type)?.try_into()?;
        let needs_backup: bool = kwargs
            .get(Qstr::MP_QSTR_needs_backup)
            .map(TryInto::try_into)
            .unwrap_or(Ok(false))?;
        let no_backup: bool = kwargs
            .get(Qstr::MP_QSTR_no_backup)
            .map(TryInto::try_into)
            .unwrap_or(Ok(false))?;

        VERSION.set(STORAGE_VERSION_CURRENT)?;
        MNEMONIC_SECRET.set(secret.try_into()?)?;
        BACKUP_TYPE.set(backup_type)?;
        set_true_or_delete(NO_BACKUP, no_backup)?;
        INITIALIZED.set(true)?;

        if !no_backup {
            set_true_or_delete(NEEDS_BACKUP, needs_backup)?;
        }

        Ok(Obj::const_none())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn is_passphrase_enabled() -> Obj {
    USE_PASSPHRASE.get().unwrap_or(false).into()
}

extern "C" fn set_passphrase_enabled(enable: Obj) -> Obj {
    let block = || {
        let enable = enable.try_into()?;

        USE_PASSPHRASE.set(enable)?;

        if !enable {
            PASSPHRASE_ALWAYS_ON_DEVICE.set(false)?;
        }

        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_passphrase_always_on_device() -> Obj {
    PASSPHRASE_ALWAYS_ON_DEVICE.get().unwrap_or(false).into()
}

extern "C" fn set_passphrase_always_on_device(enable: Obj) -> Obj {
    let block = || {
        PASSPHRASE_ALWAYS_ON_DEVICE
            .set(enable.try_into()?)?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn unfinished_backup() -> Obj {
    UNFINISHED_BACKUP.get().unwrap_or(false).into()
}

extern "C" fn set_unfinished_backup(state: Obj) -> Obj {
    let block = || UNFINISHED_BACKUP.set(state.try_into()?)?.try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn needs_backup() -> Obj {
    NEEDS_BACKUP.get().unwrap_or(false).into()
}

extern "C" fn set_backed_up() -> Obj {
    let block = || NEEDS_BACKUP.delete()?.try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn no_backup() -> Obj {
    NO_BACKUP.get().unwrap_or(false).into()
}

extern "C" fn get_experimental_features() -> Obj {
    EXPERIMENTAL_FEATURES.get().unwrap_or(false).into()
}

extern "C" fn set_experimental_features(enable: Obj) -> Obj {
    let block = || set_true_or_delete(EXPERIMENTAL_FEATURES, enable.try_into()?)?.try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_backup_type() -> Obj {
    let block = || {
        // TODO: we could import the BackupType enum
        let backup_type = BACKUP_TYPE.get().unwrap_or(0);

        if ![0, 1, 2].contains(&backup_type) {
            Err(Error::ValueError(cstr!("Invalid backup type")))
        } else {
            Ok(backup_type.into())
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_homescreen() -> Obj {
    let block = || HOMESCREEN.get().try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_homescreen(homescreen: Obj) -> Obj {
    let block = || {
        HOMESCREEN
            .set(Buffer::try_from(homescreen)?.try_into()?)?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_slip39_identifier() -> Obj {
    SLIP39_IDENTIFIER.get().into()
}

extern "C" fn set_slip39_identifier(identifier: Obj) -> Obj {
    let block = || SLIP39_IDENTIFIER.set(identifier.try_into()?)?.try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_slip39_iteration_exponent() -> Obj {
    SLIP39_ITERATION_EXPONENT.get().into()
}

extern "C" fn set_slip39_iteration_exponent(exponent: Obj) -> Obj {
    let block = || {
        SLIP39_ITERATION_EXPONENT
            .set(exponent.try_into()?)?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_autolock_delay_ms() -> Obj {
    let block = || {
        AUTOLOCK_DELAY_MS
            .get()
            .unwrap_or(AUTOLOCK_DELAY_DEFAULT)
            .clamp(AUTOLOCK_DELAY_MINIMUM, AUTOLOCK_DELAY_MAXIMUM)
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_autolock_delay_ms(delay_ms: Obj) -> Obj {
    let block = || AUTOLOCK_DELAY_MS.set(delay_ms.try_into()?)?.try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_flags() -> Obj {
    let block = || FLAGS.get().unwrap_or(0).try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_flags(flags: Obj) -> Obj {
    let block = || {
        let flags: u32 = flags.try_into()?;

        let old_flags = FLAGS.get().unwrap_or(0);

        // Not deleting old flags
        let new_flags = flags | old_flags;
        FLAGS.set(new_flags)?.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_safety_check_level() -> Obj {
    let level = SAFETY_CHECK_LEVEL
        .get()
        .unwrap_or(DEFAULT_SAFETY_CHECK_LEVEL);

    if !SAFETY_CHECK_LEVELS.contains(&level) {
        DEFAULT_SAFETY_CHECK_LEVEL.into()
    } else {
        level.into()
    }
}

extern "C" fn set_safety_check_level(level: Obj) -> Obj {
    let block = || {
        let level = level.try_into()?;

        if !SAFETY_CHECK_LEVELS.contains(&level) {
            Err(Error::ValueError(cstr!("Not valid safety level")))
        } else {
            SAFETY_CHECK_LEVEL.set(level)?.try_into()
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_sd_salt_auth_key() -> Obj {
    let block = || SD_SALT_AUTH_KEY.get().try_into();
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_sd_salt_auth_key(auth_key: Obj) -> Obj {
    let block = || {
        let auth_key: Buffer = auth_key.try_into()?;

        if auth_key.is_empty() {
            SD_SALT_AUTH_KEY.delete()?.try_into()
        } else {
            SD_SALT_AUTH_KEY.set(auth_key.try_into()?)?.try_into()
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_next_u2f_counter() -> Obj {
    let block = || {
        Counter::public_writable(APP_DEVICE, U2F_COUNTER)
            .get_and_increment()?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn set_u2f_counter(count: Obj) -> Obj {
    let block = || {
        Counter::public_writable(APP_DEVICE, U2F_COUNTER)
            .set(count.try_into()?)?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn get_private_u2f_counter() -> Obj {
    U2F_COUNTER_PRIVATE.get().into()
}

extern "C" fn delete_private_u2f_counter() -> Obj {
    let block = || U2F_COUNTER_PRIVATE.delete()?.try_into();
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub static mp_module_trezorstoragedevice: Module = obj_module! {
    Qstr::MP_QSTR___name_storage__ => Qstr::MP_QSTR_trezorstoragedevice.to_obj(),

    /// BackupTypeInt = TypeVar("BackupTypeInt", bound=int)
    /// StorageSafetyCheckLevel = Literal[0, 1]

    /// def is_version_stored() -> bool:
    ///     """Whether version is in storage."""
    Qstr::MP_QSTR_is_version_stored => obj_fn_0!(is_version_stored).as_obj(),

    /// def is_initialized() -> bool:
    ///     """Whether device is initialized."""
    Qstr::MP_QSTR_is_initialized => obj_fn_0!(is_initialized).as_obj(),

    /// def set_is_initialized(is_initialized: bool) -> None:
    ///     """Whether device is initialized."""
    Qstr::MP_QSTR_set_is_initialized => obj_fn_1!(set_is_initialized).as_obj(),

    /// def get_version() -> bytes | None:
    ///     """Get version."""
    Qstr::MP_QSTR_get_version => obj_fn_0!(get_version).as_obj(),

    /// def set_version(version: bytes) -> None:
    ///     """Set version."""
    Qstr::MP_QSTR_set_version => obj_fn_1!(set_version).as_obj(),

    /// def get_rotation() -> int:
    ///     """Get rotation."""
    Qstr::MP_QSTR_get_rotation => obj_fn_0!(get_rotation).as_obj(),

    /// def set_rotation(rotation: int) -> None:
    ///     """Set rotation."""
    Qstr::MP_QSTR_set_rotation => obj_fn_1!(set_rotation).as_obj(),

    /// def get_label() -> str | None:
    ///     """Get label."""
    Qstr::MP_QSTR_get_label => obj_fn_0!(get_label).as_obj(),

    /// def set_label(label: str) -> None:
    ///     """Set label."""
    Qstr::MP_QSTR_set_label => obj_fn_1!(set_label).as_obj(),

    /// def get_device_id() -> str:
    ///     """Get device ID."""
    Qstr::MP_QSTR_get_device_id => obj_fn_0!(get_device_id).as_obj(),

    /// def set_device_id(device_id: str) -> None:
    ///     """Set device ID."""
    Qstr::MP_QSTR_set_device_id => obj_fn_1!(set_device_id).as_obj(),

    /// def get_mnemonic_secret() -> bytes | None:
    ///     """Get mnemonic secret."""
    Qstr::MP_QSTR_get_mnemonic_secret => obj_fn_0!(get_mnemonic_secret).as_obj(),

    /// def set_mnemonic_secret(
    ///     *,
    ///     secret: bytes,
    ///     backup_type: BackupTypeInt,
    ///     needs_backup: bool = False,
    ///     no_backup: bool = False,
    /// ) -> None:
    ///     """Set mnemonic secret. Only kwargs are supported."""
    Qstr::MP_QSTR_set_mnemonic_secret => obj_fn_kw!(0, set_mnemonic_secret).as_obj(),

    /// def is_passphrase_enabled() -> bool:
    ///     """Whether passphrase is enabled."""
    Qstr::MP_QSTR_is_passphrase_enabled => obj_fn_0!(is_passphrase_enabled).as_obj(),

    /// def set_passphrase_enabled(enable: bool) -> None:
    ///     """Set whether passphrase is enabled."""
    Qstr::MP_QSTR_set_passphrase_enabled => obj_fn_1!(set_passphrase_enabled).as_obj(),

    /// def get_passphrase_always_on_device() -> bool:
    ///     """Whether passphrase is on device."""
    Qstr::MP_QSTR_get_passphrase_always_on_device => obj_fn_0!(get_passphrase_always_on_device).as_obj(),

    /// def set_passphrase_always_on_device(enable: bool) -> None:
    ///     """Set whether passphrase is on device.
    ///
    ///     This is backwards compatible with _PASSPHRASE_SOURCE:
    ///     - If ASK(0) => returns False, the check against b"\x01" in get_bool fails.
    ///     - If DEVICE(1) => returns True, the check against b"\x01" in get_bool succeeds.
    ///     - If HOST(2) => returns False, the check against b"\x01" in get_bool fails.
    ///     """
    Qstr::MP_QSTR_set_passphrase_always_on_device => obj_fn_1!(set_passphrase_always_on_device).as_obj(),

    /// def unfinished_backup() -> bool:
    ///     """Whether backup is still in progress."""
    Qstr::MP_QSTR_unfinished_backup => obj_fn_0!(unfinished_backup).as_obj(),

    /// def set_unfinished_backup(state: bool) -> None:
    ///     """Set backup state."""
    Qstr::MP_QSTR_set_unfinished_backup => obj_fn_1!(set_unfinished_backup).as_obj(),

    /// def needs_backup() -> bool:
    ///     """Whether backup is needed."""
    Qstr::MP_QSTR_needs_backup => obj_fn_0!(needs_backup).as_obj(),

    /// def set_backed_up() -> None:
    ///     """Signal that backup is finished."""
    Qstr::MP_QSTR_set_backed_up => obj_fn_0!(set_backed_up).as_obj(),

    /// def no_backup() -> bool:
    ///     """Whether there is no backup."""
    Qstr::MP_QSTR_no_backup => obj_fn_0!(no_backup).as_obj(),

    /// def get_backup_type() -> BackupTypeInt:
    ///     """Get backup type."""
    Qstr::MP_QSTR_get_backup_type => obj_fn_0!(get_backup_type).as_obj(),

    /// def get_homescreen() -> bytes | None:
    ///     """Get homescreen."""
    Qstr::MP_QSTR_get_homescreen => obj_fn_0!(get_homescreen).as_obj(),

    /// def set_homescreen(homescreen: bytes) -> None:
    ///     """Set homescreen."""
    Qstr::MP_QSTR_set_homescreen => obj_fn_1!(set_homescreen).as_obj(),

    /// def get_slip39_identifier() -> int | None:
    ///     """The device's actual SLIP-39 identifier used in passphrase derivation."""
    Qstr::MP_QSTR_get_slip39_identifier => obj_fn_0!(get_slip39_identifier).as_obj(),

    /// def set_slip39_identifier(identifier: int) -> None:
    ///     """
    ///     The device's actual SLIP-39 identifier used in passphrase derivation.
    ///     Not to be confused with recovery.identifier, which is stored only during
    ///     the recovery process and it is copied here upon success.
    ///     """
    Qstr::MP_QSTR_set_slip39_identifier => obj_fn_1!(set_slip39_identifier).as_obj(),

    /// def get_slip39_iteration_exponent() -> int | None:
    ///     """The device's actual SLIP-39 iteration exponent used in passphrase derivation."""
    Qstr::MP_QSTR_get_slip39_iteration_exponent => obj_fn_0!(get_slip39_iteration_exponent).as_obj(),

    /// def set_slip39_iteration_exponent(exponent: int) -> None:
    ///     """
    ///     The device's actual SLIP-39 iteration exponent used in passphrase derivation.
    ///     Not to be confused with recovery.iteration_exponent, which is stored only during
    ///     the recovery process and it is copied here upon success.
    ///     """
    Qstr::MP_QSTR_set_slip39_iteration_exponent => obj_fn_1!(set_slip39_iteration_exponent).as_obj(),

    /// def get_autolock_delay_ms() -> int:
    ///     """Get autolock delay."""
    Qstr::MP_QSTR_get_autolock_delay_ms => obj_fn_0!(get_autolock_delay_ms).as_obj(),

    /// def set_autolock_delay_ms(delay_ms: int) -> None:
    ///     """Set autolock delay."""
    Qstr::MP_QSTR_set_autolock_delay_ms => obj_fn_1!(set_autolock_delay_ms).as_obj(),

    /// def get_flags() -> int:
    ///     """Get flags."""
    Qstr::MP_QSTR_get_flags => obj_fn_0!(get_flags).as_obj(),

    /// def set_flags(flags: int) -> None:
    ///     """Set flags."""
    Qstr::MP_QSTR_set_flags => obj_fn_1!(set_flags).as_obj(),

    /// def get_safety_check_level() -> StorageSafetyCheckLevel:
    ///     """Get safety check level.
    ///     Do not use this function directly, see apps.common.safety_checks instead.
    ///     """
    Qstr::MP_QSTR_get_safety_check_level => obj_fn_0!(get_safety_check_level).as_obj(),

    /// def set_safety_check_level(level: StorageSafetyCheckLevel) -> None:
    ///     """Set safety check level.
    ///     Do not use this function directly, see apps.common.safety_checks instead.
    ///     """
    Qstr::MP_QSTR_set_safety_check_level => obj_fn_1!(set_safety_check_level).as_obj(),

    /// def get_sd_salt_auth_key() -> bytes | None:
    ///     """The key used to check the authenticity of the SD card salt."""
    Qstr::MP_QSTR_get_sd_salt_auth_key => obj_fn_0!(get_sd_salt_auth_key).as_obj(),

    /// def set_sd_salt_auth_key(auth_key: bytes) -> None:
    ///     """The key used to check the authenticity of the SD card salt.
    ///     Empty bytes will delete the salt.
    ///     """
    Qstr::MP_QSTR_set_sd_salt_auth_key => obj_fn_1!(set_sd_salt_auth_key).as_obj(),

    /// def get_next_u2f_counter() -> int:
    ///     """Get next U2F counter."""
    Qstr::MP_QSTR_get_next_u2f_counter => obj_fn_0!(get_next_u2f_counter).as_obj(),

    /// def set_u2f_counter(count: int) -> None:
    ///     """Set U2F counter."""
    Qstr::MP_QSTR_set_u2f_counter => obj_fn_1!(set_u2f_counter).as_obj(),

    /// def get_private_u2f_counter() -> int | None:
    ///     """Get private U2F counter."""
    Qstr::MP_QSTR_get_private_u2f_counter => obj_fn_0!(get_private_u2f_counter).as_obj(),

    /// def delete_private_u2f_counter() -> None:
    ///     """Delete private U2F counter."""
    Qstr::MP_QSTR_delete_private_u2f_counter => obj_fn_0!(delete_private_u2f_counter).as_obj(),

    /// def get_experimental_features() -> bool:
    ///     """Whether we have experimental features."""
    Qstr::MP_QSTR_get_experimental_features => obj_fn_0!(get_experimental_features).as_obj(),

    /// def set_experimental_features(enabled: bool) -> None:
    ///     """Set experimental features."""
    Qstr::MP_QSTR_set_experimental_features => obj_fn_1!(set_experimental_features).as_obj(),
};
