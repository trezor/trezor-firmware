from micropython import const

from trezor import config

_STORAGE_VERSION = b'\x01'

_APP            = const(0x0001)  # app namespace
_DEVICE_ID      = const(0x0000)  # bytes
_VERSION        = const(0x0001)  # int
_MNEMONIC       = const(0x0002)  # str
_LANGUAGE       = const(0x0003)  # str
_LABEL          = const(0x0004)  # str
_USE_PASSPHRASE = const(0x0005)  # 0x01 or empty


def get_device_id() -> str:
    dev_id = config.get(_APP, _DEVICE_ID).decode()
    if not dev_id:
        dev_id = new_device_id()
        config.set(_APP, _DEVICE_ID, dev_id.encode())
    return dev_id


def is_initialized() -> bool:
    return bool(config.get(_APP, _VERSION))


def get_label() -> str:
    return config.get(_APP, _LABEL).decode()


def get_mnemonic() -> str:
    return config.get(_APP, _MNEMONIC).decode()


def has_passphrase() -> bool:
    return bool(config.get(_APP, _USE_PASSPHRASE))


def load_mnemonic(mnemonic: str):
    config.set(_APP, _VERSION, _STORAGE_VERSION)
    config.set(_APP, _MNEMONIC, mnemonic.encode())


def load_settings(label: str = None, use_passphrase: bool = None):
    if label is not None:
        config.set(_APP, _LABEL, label.encode())
    if use_passphrase is True:
        config.set(_APP, _USE_PASSPHRASE, b'\x01')
    if use_passphrase is False:
        config.set(_APP, _USE_PASSPHRASE, b'')


def change_pin(pin: str, newpin: str):
    return config.change_pin(pin, newpin)


def wipe():
    from . import cache
    config.wipe()
    cache.clear()


def new_device_id() -> str:
    from ubinascii import hexlify
    from trezor.crypto import random
    return hexlify(random.bytes(12)).decode('ascii').upper()
