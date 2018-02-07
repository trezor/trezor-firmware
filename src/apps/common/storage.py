from micropython import const

from trezor import config

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


def get_device_id() -> str:
    dev_id = config.get(_APP, _DEVICE_ID, True).decode()  # public
    if not dev_id:
        dev_id = new_device_id()
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


def load_mnemonic(mnemonic: str, needs_backup: bool):
    config.set(_APP, _MNEMONIC, mnemonic.encode())
    config.set(_APP, _VERSION, _STORAGE_VERSION)
    if needs_backup:
        config.set(_APP, _NEEDS_BACKUP, b'\x01')
    else:
        config.set(_APP, _NEEDS_BACKUP, b'')


def load_settings(label: str=None, use_passphrase: bool=None, homescreen: bytes=None):
    if label is not None:
        config.set(_APP, _LABEL, label.encode(), True)  # public
    if use_passphrase is True:
        config.set(_APP, _USE_PASSPHRASE, b'\x01')
    if use_passphrase is False:
        config.set(_APP, _USE_PASSPHRASE, b'')
    if homescreen is not None:
        if homescreen[:8] == b'TOIf\x90\x00\x90\x00':
            config.set(_APP, _HOMESCREEN, homescreen, True)  # public
        else:
            config.set(_APP, _HOMESCREEN, b'', True)  # public


def wipe():
    from . import cache
    config.wipe()
    cache.clear()


def new_device_id() -> str:
    from ubinascii import hexlify
    from trezor.crypto import random
    return hexlify(random.bytes(12)).decode().upper()
