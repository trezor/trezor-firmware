from micropython import const
from ubinascii import hexlify

from storage import common
from trezor.crypto import random
from trezor.messages import BackupType

if False:
    from trezor.messages.ResetDevice import EnumTypeBackupType
    from typing import Optional

# Namespace:
_NAMESPACE = common.APP_DEVICE

# fmt: off
# Keys:
_DEVICE_ID                 = const(0x00)  # bytes
_VERSION                   = const(0x01)  # int
_MNEMONIC_SECRET           = const(0x02)  # bytes
_LANGUAGE                  = const(0x03)  # str
_LABEL                     = const(0x04)  # str
_USE_PASSPHRASE            = const(0x05)  # bool (0x01 or empty)
_HOMESCREEN                = const(0x06)  # bytes
_NEEDS_BACKUP              = const(0x07)  # bool (0x01 or empty)
_FLAGS                     = const(0x08)  # int
U2F_COUNTER                = const(0x09)  # int
_PASSPHRASE_SOURCE         = const(0x0A)  # int
_UNFINISHED_BACKUP         = const(0x0B)  # bool (0x01 or empty)
_AUTOLOCK_DELAY_MS         = const(0x0C)  # int
_NO_BACKUP                 = const(0x0D)  # bool (0x01 or empty)
_BACKUP_TYPE               = const(0x0E)  # int
_ROTATION                  = const(0x0F)  # int
_SLIP39_IDENTIFIER         = const(0x10)  # bool
_SLIP39_ITERATION_EXPONENT = const(0x11)  # int
_SD_SALT_AUTH_KEY          = const(0x12)  # bytes

_DEFAULT_BACKUP_TYPE       = BackupType.Bip39
# fmt: on

HOMESCREEN_MAXSIZE = 16384

# Length of SD salt auth tag.
# Other SD-salt-related constants are in sd_salt.py
SD_SALT_AUTH_KEY_LEN_BYTES = const(16)


def is_version_stored() -> bool:
    return bool(common.get(_NAMESPACE, _VERSION))


def get_version() -> Optional[bytes]:
    return common.get(_NAMESPACE, _VERSION)


def set_version(version: bytes) -> None:
    common.set(_NAMESPACE, _VERSION, version)


def _new_device_id() -> str:
    return hexlify(random.bytes(12)).decode().upper()


def get_device_id() -> str:
    dev_id = common.get(_NAMESPACE, _DEVICE_ID, True)  # public
    if not dev_id:
        dev_id = _new_device_id().encode()
        common.set(_NAMESPACE, _DEVICE_ID, dev_id, True)  # public
    return dev_id.decode()


def get_rotation() -> int:
    rotation = common.get(_NAMESPACE, _ROTATION, True)  # public
    if not rotation:
        return 0
    return int.from_bytes(rotation, "big")


def get_label() -> Optional[str]:
    label = common.get(_NAMESPACE, _LABEL, True)  # public
    if label is None:
        return None
    return label.decode()


def get_mnemonic_secret() -> Optional[bytes]:
    return common.get(_NAMESPACE, _MNEMONIC_SECRET)


def get_backup_type() -> EnumTypeBackupType:
    backup_type = common.get_uint8(_NAMESPACE, _BACKUP_TYPE)
    if backup_type is None:
        backup_type = _DEFAULT_BACKUP_TYPE

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


def get_homescreen() -> Optional[bytes]:
    return common.get(_NAMESPACE, _HOMESCREEN, True)  # public


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


def get_passphrase_source() -> int:
    b = common.get(_NAMESPACE, _PASSPHRASE_SOURCE)
    if b == b"\x01":
        return 1
    elif b == b"\x02":
        return 2
    else:
        return 0


def load_settings(
    label: str = None,
    use_passphrase: bool = None,
    homescreen: bytes = None,
    passphrase_source: int = None,
    display_rotation: int = None,
) -> None:
    if label is not None:
        common.set(_NAMESPACE, _LABEL, label.encode(), True)  # public
    if use_passphrase is not None:
        common.set_bool(_NAMESPACE, _USE_PASSPHRASE, use_passphrase)
    if homescreen is not None:
        if homescreen[:8] == b"TOIf\x90\x00\x90\x00":
            if len(homescreen) <= HOMESCREEN_MAXSIZE:
                common.set(_NAMESPACE, _HOMESCREEN, homescreen, True)  # public
        else:
            common.set(_NAMESPACE, _HOMESCREEN, b"", True)  # public
    if passphrase_source is not None:
        if passphrase_source in (0, 1, 2):
            common.set(_NAMESPACE, _PASSPHRASE_SOURCE, bytes([passphrase_source]))
    if display_rotation is not None:
        if display_rotation not in (0, 90, 180, 270):
            raise ValueError(
                "Unsupported display rotation degrees: %d" % display_rotation
            )
        else:
            common.set(
                _NAMESPACE, _ROTATION, display_rotation.to_bytes(2, "big"), True
            )  # public


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
    flags = (flags | i) & 0xFFFFFFFF
    if flags != i:
        common.set(_NAMESPACE, _FLAGS, flags.to_bytes(4, "big"))


def get_autolock_delay_ms() -> int:
    b = common.get(_NAMESPACE, _AUTOLOCK_DELAY_MS)
    if b is None:
        return 10 * 60 * 1000
    else:
        return int.from_bytes(b, "big")


def set_autolock_delay_ms(delay_ms: int) -> None:
    if delay_ms < 60 * 1000:
        delay_ms = 60 * 1000
    common.set(_NAMESPACE, _AUTOLOCK_DELAY_MS, delay_ms.to_bytes(4, "big"))


def next_u2f_counter() -> Optional[int]:
    return common.next_counter(_NAMESPACE, U2F_COUNTER, True)  # writable when locked


def set_u2f_counter(count: int) -> None:
    common.set_counter(_NAMESPACE, U2F_COUNTER, count, True)  # writable when locked


def set_slip39_identifier(identifier: int) -> None:
    """
    The device's actual SLIP-39 identifier used in passphrase derivation.
    Not to be confused with recovery.identifier, which is stored only during
    the recovery process and it is copied here upon success.
    """
    common.set_uint16(_NAMESPACE, _SLIP39_IDENTIFIER, identifier)


def get_slip39_identifier() -> Optional[int]:
    """The device's actual SLIP-39 identifier used in passphrase derivation."""
    return common.get_uint16(_NAMESPACE, _SLIP39_IDENTIFIER)


def set_slip39_iteration_exponent(exponent: int) -> None:
    """
    The device's actual SLIP-39 iteration exponent used in passphrase derivation.
    Not to be confused with recovery.iteration_exponent, which is stored only during
    the recovery process and it is copied here upon success.
    """
    common.set_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT, exponent)


def get_slip39_iteration_exponent() -> Optional[int]:
    """
    The device's actual SLIP-39 iteration exponent used in passphrase derivation.
    """
    return common.get_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT)


def get_sd_salt_auth_key() -> Optional[bytes]:
    """
    The key used to check the authenticity of the SD card salt.
    """
    auth_key = common.get(_NAMESPACE, _SD_SALT_AUTH_KEY, public=True)
    if auth_key is not None and len(auth_key) != SD_SALT_AUTH_KEY_LEN_BYTES:
        raise ValueError
    return auth_key


def set_sd_salt_auth_key(auth_key: Optional[bytes]) -> None:
    """
    The key used to check the authenticity of the SD card salt.
    """
    if auth_key is not None:
        if len(auth_key) != SD_SALT_AUTH_KEY_LEN_BYTES:
            raise ValueError
        return common.set(_NAMESPACE, _SD_SALT_AUTH_KEY, auth_key, public=True)
    else:
        return common.delete(_NAMESPACE, _SD_SALT_AUTH_KEY, public=True)
