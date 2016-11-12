import protobuf as p
from micropython import const
from trezor import config

_APP_COMMON = const(1)

_CFG_ID = const(0)
_CFG_VERSION = const(1)
_CFG_MNEMONIC = const(2)
_CFG_LANGUAGE = const(3)
_CFG_LABEL = const(4)
_CFG_PIN = const(5)
_CFG_PIN_ATTEMPTS = const(6)
_CFG_PASSPHRASE_PROTECTION = const(7)

_types = {
    _CFG_ID: p.UnicodeType,
    _CFG_VERSION: p.UVarintType,
    _CFG_MNEMONIC: p.UnicodeType,
    _CFG_LANGUAGE: p.UnicodeType,
    _CFG_LABEL: p.UnicodeType,
    _CFG_PIN: p.UnicodeType,
    _CFG_PIN_ATTEMPTS: p.UVarintType,
    _CFG_PASSPHRASE_PROTECTION: p.BoolType,
}


def get_device_id() -> str:
    devid = _get(_CFG_ID)
    if devid is None:
        devid = _new_device_id()
        _set(_CFG_ID, devid)
    return devid


def is_initialized() -> bool:
    return _get(_CFG_VERSION) is not None


def is_protected_by_pin() -> bool:
    return _get(_CFG_PIN) is not None


def is_protected_by_passphrase() -> bool:
    return _get(_CFG_PASSPHRASE_PROTECTION) is True


def check_pin(pin: str) -> bool:
    return _get(_CFG_PIN) == pin


def get_label() -> str:
    return _get(_CFG_LABEL)


def get_mnemonic() -> str:
    return _get(_CFG_MNEMONIC)


def load_mnemonic(mnemonic: str):
    if is_initialized():
        raise Exception('Device is already initialized')
    _set(_CFG_VERSION, 1)
    _set(_CFG_MNEMONIC, mnemonic)


def load_settings(language: str,
                  label: str,
                  pin: str,
                  passphrase_protection: bool):
    if not is_initialized():
        raise Exception('Device is not initialized')
    _set(_CFG_LANGUAGE, language or None)
    _set(_CFG_LABEL, label or None)
    _set(_CFG_PIN, pin or None)
    _set(_CFG_PIN_ATTEMPTS, None)
    _set(_CFG_PASSPHRASE_PROTECTION, passphrase_protection)


def wipe():
    _set(_CFG_ID, _new_device_id())
    _set(_CFG_VERSION, None)
    _set(_CFG_MNEMONIC, None)
    _set(_CFG_LANGUAGE, None)
    _set(_CFG_LABEL, None)
    _set(_CFG_PIN, None)
    _set(_CFG_PIN_ATTEMPTS, None)
    _set(_CFG_PASSPHRASE_PROTECTION, None)


def _get(key: int):
    buf = config.get(_APP_COMMON, key)
    if buf:
        val = _types[key].loads(buf)
    else:
        val = None
    return val


def _set(key: int, val):
    if val is not None:
        buf = _types[key].dumps(val)
    else:
        buf = b''
    config.set(_APP_COMMON, key, buf)


def _new_device_id() -> str:
    from ubinascii import hexlify
    from trezor.crypto import random
    return hexlify(random.bytes(12)).decode('ascii').upper()
