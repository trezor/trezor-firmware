from typing import *
BackupTypeInt = TypeVar("BackupTypeInt", bound=int)
StorageSafetyCheckLevel = Literal[0, 1]


# rust/src/storagedevice/storage_device.rs
def is_version_stored() -> bool:
    """Whether version is in storage."""


# rust/src/storagedevice/storage_device.rs
def is_initialized() -> bool:
    """Whether device is initialized."""


# rust/src/storagedevice/storage_device.rs
def get_version() -> bytes:
    """Get version."""


# rust/src/storagedevice/storage_device.rs
def set_version(version: bytes) -> None:
    """Set version."""


# rust/src/storagedevice/storage_device.rs
def get_rotation() -> int:
    """Get rotation."""


# rust/src/storagedevice/storage_device.rs
def set_rotation(rotation: int) -> None:
    """Set rotation."""


# rust/src/storagedevice/storage_device.rs
def get_label() -> str | None:
    """Get label."""


# rust/src/storagedevice/storage_device.rs
def set_label(label: str) -> None:
    """Set label."""


# rust/src/storagedevice/storage_device.rs
def get_device_id() -> str:
    """Get device ID."""


# rust/src/storagedevice/storage_device.rs
def get_mnemonic_secret() -> bytes:
    """Get mnemonic secret."""


# rust/src/storagedevice/storage_device.rs
def set_mnemonic_secret(
    secret: bytes,
    backup_type: BackupTypeInt,
    needs_backup: bool = False,
    no_backup: bool = False,
) -> None:
    """Set mnemonic secret"""


# rust/src/storagedevice/storage_device.rs
def is_passphrase_enabled() -> bool:
    """Whether passphrase is enabled."""


# rust/src/storagedevice/storage_device.rs
def set_passphrase_enabled(enable: bool) -> None:
    """Set whether passphrase is enabled."""


# rust/src/storagedevice/storage_device.rs
def get_passphrase_always_on_device() -> bool:
    """Whether passphrase is on device."""


# rust/src/storagedevice/storage_device.rs
def set_passphrase_always_on_device(enable: bool) -> None:
    """Set whether passphrase is on device.
    This is backwards compatible with _PASSPHRASE_SOURCE:
    - If ASK(0) => returns False, the check against b"\x01" in get_bool fails.
    - If DEVICE(1) => returns True, the check against b"\x01" in get_bool succeeds.
    - If HOST(2) => returns False, the check against b"\x01" in get_bool fails.
    """


# rust/src/storagedevice/storage_device.rs
def unfinished_backup() -> bool:
    """Whether backup is still in progress."""


# rust/src/storagedevice/storage_device.rs
def set_unfinished_backup(state: bool) -> None:
    """Set backup state."""


# rust/src/storagedevice/storage_device.rs
def needs_backup() -> bool:
    """Whether backup is needed."""


# rust/src/storagedevice/storage_device.rs
def set_backed_up() -> None:
    """Signal that backup is finished."""


# rust/src/storagedevice/storage_device.rs
def no_backup() -> bool:
    """Whether there is no backup."""


# rust/src/storagedevice/storage_device.rs
def get_backup_type() -> BackupTypeInt:
    """Get backup type."""


# rust/src/storagedevice/storage_device.rs
def get_homescreen() -> bytes | None:
    """Get homescreen."""


# rust/src/storagedevice/storage_device.rs
def set_homescreen(homescreen: bytes) -> None:
    """Set homescreen."""


# rust/src/storagedevice/storage_device.rs
def get_slip39_identifier() -> int | None:
    """The device's actual SLIP-39 identifier used in passphrase derivation."""


# rust/src/storagedevice/storage_device.rs
def set_slip39_identifier(identifier: int) -> None:
    """
    The device's actual SLIP-39 identifier used in passphrase derivation.
    Not to be confused with recovery.identifier, which is stored only during
    the recovery process and it is copied here upon success.
    """


# rust/src/storagedevice/storage_device.rs
def get_slip39_iteration_exponent() -> int | None:
    """The device's actual SLIP-39 iteration exponent used in passphrase derivation."""


# rust/src/storagedevice/storage_device.rs
def set_slip39_iteration_exponent(exponent: int) -> None:
    """
    The device's actual SLIP-39 iteration exponent used in passphrase derivation.
    Not to be confused with recovery.iteration_exponent, which is stored only during
    the recovery process and it is copied here upon success.
    """


# rust/src/storagedevice/storage_device.rs
def get_autolock_delay_ms() -> int:
    """Get autolock delay."""


# rust/src/storagedevice/storage_device.rs
def set_autolock_delay_ms(delay_ms: int) -> None:
    """Set autolock delay."""


# rust/src/storagedevice/storage_device.rs
def get_flags() -> int:
    """Get flags."""


# rust/src/storagedevice/storage_device.rs
def set_flags(flags: int) -> None:
    """Set flags."""


# rust/src/storagedevice/storage_device.rs
def get_safety_check_level() -> StorageSafetyCheckLevel:
    """Get safety check level.
    Do not use this function directly, see apps.common.safety_checks instead.
    """


# rust/src/storagedevice/storage_device.rs
def set_safety_check_level(level: StorageSafetyCheckLevel) -> None:
    """Set safety check level.
    Do not use this function directly, see apps.common.safety_checks instead.
    """


# rust/src/storagedevice/storage_device.rs
def get_sd_salt_auth_key() -> bytes | None:
    """The key used to check the authenticity of the SD card salt."""


# rust/src/storagedevice/storage_device.rs
def set_sd_salt_auth_key(auth_key: bytes) -> None:
    """The key used to check the authenticity of the SD card salt.
    Empty bytes will delete the salt.
    """


# rust/src/storagedevice/storage_device.rs
def get_next_u2f_counter() -> int:
    """Get next U2F counter."""


# rust/src/storagedevice/storage_device.rs
def set_u2f_counter(count: int) -> None:
    """Set U2F counter."""
