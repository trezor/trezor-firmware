from micropython import const
from ubinascii import hexlify
from trezor import config
from trezor.crypto import random
from apps.common import cache

HOMESCREEN_MAXSIZE = 16384

_STORAGE_VERSION = b'\x01'

_APP            = const(0x01)  # app namespace
_DEVICE_ID      = const(0x00)  # bytes
_VERSION        = const(0x01)  # int
_MNEMONIC       = const(0x02)  # str
_LANGUAGE       = const(0x03)  # str
_LABEL          = const(0x04)  # str
_USE_PASSPHRASE = const(0x05)  # 0x01 or empty
_HOMESCREEN     = const(0x06)  # bytes
_NEEDS_BACKUP   = const(0x07)  # 0x01 or empty
_FLAGS          = const(0x08)  # int
_U2F_COUNTER    = const(0x09)  # int


def _new_device_id() -> str:
    return hexlify(random.bytes(12)).decode().upper()


def get_device_id() -> str:
    dev_id = config.get(_APP, _DEVICE_ID, True).decode()  # public
    if not dev_id:
        dev_id = _new_device_id()
        config.set(_APP, _DEVICE_ID, dev_id.encode(), True)  # public
    return dev_id


def is_initialized() -> bool:
    return bool(config.get(_APP, _VERSION))


def get_label() -> str:
    return config.get(_APP, _LABEL, True).decode()  # public


def get_mnemonic() -> str:
    return config.get(_APP, _MNEMONIC).decode()


def has_passphrase() -> bool:
    return bool(config.get(_APP, _USE_PASSPHRASE))


def get_homescreen() -> bytes:
    return config.get(_APP, _HOMESCREEN, True)  # public


def load_mnemonic(mnemonic: str, needs_backup: bool) -> None:
    config.set(_APP, _MNEMONIC, mnemonic.encode())
    config.set(_APP, _VERSION, _STORAGE_VERSION)
    if needs_backup:
        config.set(_APP, _NEEDS_BACKUP, b'\x01')
    else:
        config.set(_APP, _NEEDS_BACKUP, b'')


def needs_backup() -> bool:
    return bool(config.get(_APP, _NEEDS_BACKUP))


def set_backed_up() -> None:
    config.set(_APP, _NEEDS_BACKUP, b'')


def load_settings(label: str=None, use_passphrase: bool=None, homescreen: bytes=None) -> None:
    if label is not None:
        config.set(_APP, _LABEL, label.encode(), True)  # public
    if use_passphrase is True:
        config.set(_APP, _USE_PASSPHRASE, b'\x01')
    if use_passphrase is False:
        config.set(_APP, _USE_PASSPHRASE, b'')
    if homescreen is not None:
        if homescreen[:8] == b'TOIf\x90\x00\x90\x00':
            if len(homescreen) <= HOMESCREEN_MAXSIZE:
                config.set(_APP, _HOMESCREEN, homescreen, True)  # public
        else:
            config.set(_APP, _HOMESCREEN, b'', True)  # public


def get_flags() -> int:
    b = config.get(_APP, _FLAGS)
    if b is None:
        return 0
    else:
        return int.from_bytes(b, 'big')


def set_flags(flags: int) -> None:
    b = config.get(_APP, _FLAGS)
    if b is None:
        b = 0
    else:
        b = int.from_bytes(b, 'big')
    flags = (flags | b) & 0xFFFFFFFF
    if flags != b:
        config.set(_APP, _FLAGS, flags.to_bytes(4, 'big'))


def next_u2f_counter() -> int:
    b = config.get(_APP, _U2F_COUNTER)
    if b is None:
        b = 0
    else:
        b = int.from_bytes(b, 'big') + 1
    set_u2f_counter(b)
    return b


def set_u2f_counter(cntr: int):
    config.set(_APP, _U2F_COUNTER, cntr.to_bytes(4, 'big'))


def wipe():
    config.wipe()
    cache.clear()
