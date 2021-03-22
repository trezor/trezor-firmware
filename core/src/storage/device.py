from micropython import const
from ubinascii import hexlify

from storage import common

if False:
    from trezor.messages.ResetDevice import EnumTypeBackupType
    from typing_extensions import Literal

# Namespace:
_NAMESPACE = common.APP_DEVICE

# fmt: off
# Keys:
DEVICE_ID                  = const(0x00)  # bytes
_VERSION                   = const(0x01)  # int
_MNEMONIC_SECRET           = const(0x02)  # bytes
_LANGUAGE                  = const(0x03)  # str
_LABEL                     = const(0x04)  # str
_USE_PASSPHRASE            = const(0x05)  # bool (0x01 or empty)
_HOMESCREEN                = const(0x06)  # bytes
_NEEDS_BACKUP              = const(0x07)  # bool (0x01 or empty)
_FLAGS                     = const(0x08)  # int
U2F_COUNTER                = const(0x09)  # int
_PASSPHRASE_ALWAYS_ON_DEVICE = const(0x0A)  # bool (0x01 or empty)
_UNFINISHED_BACKUP         = const(0x0B)  # bool (0x01 or empty)
_AUTOLOCK_DELAY_MS         = const(0x0C)  # int
_NO_BACKUP                 = const(0x0D)  # bool (0x01 or empty)
_BACKUP_TYPE               = const(0x0E)  # int
_ROTATION                  = const(0x0F)  # int
_SLIP39_IDENTIFIER         = const(0x10)  # bool
_SLIP39_ITERATION_EXPONENT = const(0x11)  # int
_SD_SALT_AUTH_KEY          = const(0x12)  # bytes
INITIALIZED                = const(0x13)  # bool (0x01 or empty)
_SAFETY_CHECK_LEVEL        = const(0x14)  # int
_EXPERIMENTAL_FEATURES     = const(0x15)  # bool (0x01 or empty)

SAFETY_CHECK_LEVEL_STRICT  : Literal[0] = const(0)
SAFETY_CHECK_LEVEL_PROMPT  : Literal[1] = const(1)
_DEFAULT_SAFETY_CHECK_LEVEL = SAFETY_CHECK_LEVEL_STRICT
if False:
    StorageSafetyCheckLevel = Literal[0, 1]
# fmt: on

HOMESCREEN_MAXSIZE = 16384
LABEL_MAXLENGTH = 32

if __debug__:
    AUTOLOCK_DELAY_MINIMUM = 10 * 1000  # 10 seconds
else:
    AUTOLOCK_DELAY_MINIMUM = 60 * 1000  # 1 minute
AUTOLOCK_DELAY_DEFAULT = 10 * 60 * 1000  # 10 minutes
# autolock intervals larger than AUTOLOCK_DELAY_MAXIMUM cause issues in the scheduler
AUTOLOCK_DELAY_MAXIMUM = 0x2000_0000  # ~6 days

# Length of SD salt auth tag.
# Other SD-salt-related constants are in sd_salt.py
SD_SALT_AUTH_KEY_LEN_BYTES = const(16)


def is_version_stored() -> bool:
    return bool(common.get(_NAMESPACE, _VERSION))


def get_version() -> bytes | None:
    return common.get(_NAMESPACE, _VERSION)


def set_version(version: bytes) -> None:
    common.set(_NAMESPACE, _VERSION, version)


def is_initialized() -> bool:
    return common.get_bool(_NAMESPACE, INITIALIZED, public=True)


def _new_device_id() -> str:
    from trezorcrypto import random  # avoid pulling in trezor.crypto

    return hexlify(random.bytes(12)).decode().upper()


def get_device_id() -> str:
    dev_id = common.get(_NAMESPACE, DEVICE_ID, public=True)
    if not dev_id:
        dev_id = _new_device_id().encode()
        common.set(_NAMESPACE, DEVICE_ID, dev_id, public=True)
    return dev_id.decode()


def get_rotation() -> int:
    rotation = common.get(_NAMESPACE, _ROTATION, public=True)
    if not rotation:
        return 0
    return int.from_bytes(rotation, "big")


def set_rotation(value: int) -> None:
    if value not in (0, 90, 180, 270):
        raise ValueError  # unsupported display rotation
    common.set(_NAMESPACE, _ROTATION, value.to_bytes(2, "big"), True)  # public


def get_label() -> str | None:
    label = common.get(_NAMESPACE, _LABEL, True)  # public
    if label is None:
        return None
    return label.decode()


def set_label(label: str) -> None:
    if len(label) > LABEL_MAXLENGTH:
        raise ValueError  # label too long
    common.set(_NAMESPACE, _LABEL, label.encode(), True)  # public


def get_mnemonic_secret() -> bytes | None:
    return common.get(_NAMESPACE, _MNEMONIC_SECRET)


def get_backup_type() -> EnumTypeBackupType:
    from trezor.messages import BackupType

    backup_type = common.get_uint8(_NAMESPACE, _BACKUP_TYPE)
    if backup_type is None:
        backup_type = BackupType.Bip39

    if backup_type not in (
        BackupType.Bip39,
        BackupType.Slip39_Basic,
        BackupType.Slip39_Advanced,
    ):
        # Invalid backup type
        raise RuntimeError
    return backup_type  # type: ignore


def is_passphrase_enabled() -> bool:
    return common.get_bool(_NAMESPACE, _USE_PASSPHRASE)


def set_passphrase_enabled(enable: bool) -> None:
    common.set_bool(_NAMESPACE, _USE_PASSPHRASE, enable)
    if not enable:
        set_passphrase_always_on_device(False)


def get_homescreen() -> bytes | None:
    return common.get(_NAMESPACE, _HOMESCREEN, public=True)


def set_homescreen(homescreen: bytes) -> None:
    if len(homescreen) > HOMESCREEN_MAXSIZE:
        raise ValueError  # homescreen too large
    common.set(_NAMESPACE, _HOMESCREEN, homescreen, public=True)


def store_mnemonic_secret(
    secret: bytes,
    backup_type: EnumTypeBackupType,
    needs_backup: bool = False,
    no_backup: bool = False,
) -> None:
    set_version(common.STORAGE_VERSION_CURRENT)
    common.set(_NAMESPACE, _MNEMONIC_SECRET, secret)
    common.set_uint8(_NAMESPACE, _BACKUP_TYPE, backup_type)
    common.set_true_or_delete(_NAMESPACE, _NO_BACKUP, no_backup)
    common.set_bool(_NAMESPACE, INITIALIZED, True, public=True)
    if not no_backup:
        common.set_true_or_delete(_NAMESPACE, _NEEDS_BACKUP, needs_backup)


def needs_backup() -> bool:
    return common.get_bool(_NAMESPACE, _NEEDS_BACKUP)


def set_backed_up() -> None:
    common.delete(_NAMESPACE, _NEEDS_BACKUP)


def unfinished_backup() -> bool:
    return common.get_bool(_NAMESPACE, _UNFINISHED_BACKUP)


def set_unfinished_backup(state: bool) -> None:
    common.set_bool(_NAMESPACE, _UNFINISHED_BACKUP, state)


def no_backup() -> bool:
    return common.get_bool(_NAMESPACE, _NO_BACKUP)


def get_passphrase_always_on_device() -> bool:
    """
    This is backwards compatible with _PASSPHRASE_SOURCE:
    - If ASK(0) => returns False, the check against b"\x01" in get_bool fails.
    - If DEVICE(1) => returns True, the check against b"\x01" in get_bool succeeds.
    - If HOST(2) => returns False, the check against b"\x01" in get_bool fails.
    """
    return common.get_bool(_NAMESPACE, _PASSPHRASE_ALWAYS_ON_DEVICE)


def set_passphrase_always_on_device(enable: bool) -> None:
    common.set_bool(_NAMESPACE, _PASSPHRASE_ALWAYS_ON_DEVICE, enable)


def get_flags() -> int:
    b = common.get(_NAMESPACE, _FLAGS)
    if b is None:
        return 0
    else:
        return int.from_bytes(b, "big")


def set_flags(flags: int) -> None:
    b = common.get(_NAMESPACE, _FLAGS)
    if b is None:
        i = 0
    else:
        i = int.from_bytes(b, "big")
    flags = (flags | i) & 0xFFFF_FFFF
    if flags != i:
        common.set(_NAMESPACE, _FLAGS, flags.to_bytes(4, "big"))


def _normalize_autolock_delay(delay_ms: int) -> int:
    delay_ms = max(delay_ms, AUTOLOCK_DELAY_MINIMUM)
    delay_ms = min(delay_ms, AUTOLOCK_DELAY_MAXIMUM)
    return delay_ms


def get_autolock_delay_ms() -> int:
    b = common.get(_NAMESPACE, _AUTOLOCK_DELAY_MS)
    if b is None:
        return AUTOLOCK_DELAY_DEFAULT
    else:
        return _normalize_autolock_delay(int.from_bytes(b, "big"))


def set_autolock_delay_ms(delay_ms: int) -> None:
    delay_ms = _normalize_autolock_delay(delay_ms)
    common.set(_NAMESPACE, _AUTOLOCK_DELAY_MS, delay_ms.to_bytes(4, "big"))


def next_u2f_counter() -> int:
    return common.next_counter(_NAMESPACE, U2F_COUNTER, writable_locked=True)


def set_u2f_counter(count: int) -> None:
    common.set_counter(_NAMESPACE, U2F_COUNTER, count, writable_locked=True)


def set_slip39_identifier(identifier: int) -> None:
    """
    The device's actual SLIP-39 identifier used in passphrase derivation.
    Not to be confused with recovery.identifier, which is stored only during
    the recovery process and it is copied here upon success.
    """
    common.set_uint16(_NAMESPACE, _SLIP39_IDENTIFIER, identifier)


def get_slip39_identifier() -> int | None:
    """The device's actual SLIP-39 identifier used in passphrase derivation."""
    return common.get_uint16(_NAMESPACE, _SLIP39_IDENTIFIER)


def set_slip39_iteration_exponent(exponent: int) -> None:
    """
    The device's actual SLIP-39 iteration exponent used in passphrase derivation.
    Not to be confused with recovery.iteration_exponent, which is stored only during
    the recovery process and it is copied here upon success.
    """
    common.set_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT, exponent)


def get_slip39_iteration_exponent() -> int | None:
    """
    The device's actual SLIP-39 iteration exponent used in passphrase derivation.
    """
    return common.get_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT)


def get_sd_salt_auth_key() -> bytes | None:
    """
    The key used to check the authenticity of the SD card salt.
    """
    auth_key = common.get(_NAMESPACE, _SD_SALT_AUTH_KEY, public=True)
    if auth_key is not None and len(auth_key) != SD_SALT_AUTH_KEY_LEN_BYTES:
        raise ValueError
    return auth_key


def set_sd_salt_auth_key(auth_key: bytes | None) -> None:
    """
    The key used to check the authenticity of the SD card salt.
    """
    if auth_key is not None:
        if len(auth_key) != SD_SALT_AUTH_KEY_LEN_BYTES:
            raise ValueError
        return common.set(_NAMESPACE, _SD_SALT_AUTH_KEY, auth_key, public=True)
    else:
        return common.delete(_NAMESPACE, _SD_SALT_AUTH_KEY, public=True)


# do not use this function directly, see apps.common.safety_checks instead
def safety_check_level() -> StorageSafetyCheckLevel:
    level = common.get_uint8(_NAMESPACE, _SAFETY_CHECK_LEVEL)
    if level not in (SAFETY_CHECK_LEVEL_STRICT, SAFETY_CHECK_LEVEL_PROMPT):
        return _DEFAULT_SAFETY_CHECK_LEVEL
    else:
        return level  # type: ignore


# do not use this function directly, see apps.common.safety_checks instead
def set_safety_check_level(level: StorageSafetyCheckLevel) -> None:
    if level not in (SAFETY_CHECK_LEVEL_STRICT, SAFETY_CHECK_LEVEL_PROMPT):
        raise ValueError
    common.set_uint8(_NAMESPACE, _SAFETY_CHECK_LEVEL, level)


def get_experimental_features() -> bool:
    return common.get_bool(_NAMESPACE, _EXPERIMENTAL_FEATURES)


def set_experimental_features(enabled: bool) -> None:
    common.set_true_or_delete(_NAMESPACE, _EXPERIMENTAL_FEATURES, enabled)
