from micropython import const
import ustruct
import utime

from trezor import config
from trezor import utils

_APP = const(1)

DEVICE_ID = const(0)  # str
VERSION = const(1)  # varint
MNEMONIC = const(2)  # str
LANGUAGE = const(3)  # str
LABEL = const(4)  # str
PIN = const(5)  # bytes
PIN_FAILS = const(6)  # varint
PASSPHRASE_PROTECTION = const(7)  # varint


# pin lock
# ===

_locked = True


def is_locked() -> bool:
    return is_protected_by_pin() and _locked


def unlock(user_pin: str, failure_callback=None) -> bool:
    global _locked

    if not is_protected_by_pin():
        return True

    # increment the pin fail counter before checking the pin
    fails = bytes_to_int(config_get(PIN_FAILS)) + 1
    config_set_checked(PIN_FAILS, int_to_bytes(fails))

    if const_equal(config_get(PIN), user_pin.encode()):
        # unlock and reset the counter
        _locked = False
        config_set(PIN_FAILS, int_to_bytes(0))
        return True

    else:
        # lock, run the callback (ie for ui) and sleep for a quadratic delay
        _locked = True
        delay_ms = fails * fails * 1000
        try:
            if failure_callback:
                failure_callback(delay_ms)
        finally:
            utime.sleep_ms(delay_ms)
        return False


def lock():
    global _locked
    _locked = True


def const_equal(a: bytes, b: bytes) -> bool:
    return a == b  # TODO: proper const equal


# settings
# ===


def get_device_id() -> str:
    dev_id = config_get(DEVICE_ID).decode()
    if not dev_id:
        dev_id = new_device_id()
        config_set(DEVICE_ID, dev_id.encode())
    return dev_id


def is_initialized() -> bool:
    return bool(config_get(VERSION))


def is_protected_by_pin() -> bool:
    return bool(config_get(PIN))


def is_protected_by_passphrase() -> bool:
    return bool(bytes_to_int(config_get(PASSPHRASE_PROTECTION)))


def get_pin() -> str:
    return config_get(PIN).decode()


def get_label() -> str:
    return config_get(LABEL).decode()


def get_language() -> str:
    return config_get(LANGUAGE).decode() or _DEFAULT_LANGUAGE


def get_mnemonic() -> str:
    utils.ensure(is_initialized())
    utils.ensure(not is_locked())

    return config_get(MNEMONIC).decode()


# settings configuration
# ===


def load_mnemonic(mnemonic: str):
    utils.ensure(not is_initialized())

    config_set(VERSION, int_to_bytes(1))
    config_set(MNEMONIC, mnemonic.encode())


_ALLOWED_LANGUAGES = ('english')
_DEFAULT_LANGUAGE = 'english'


def load_settings(language: str=None,
                  label: str=None,
                  pin: str=None,
                  passphrase_protection: bool=None):
    utils.ensure(is_initialized())
    utils.ensure(not is_locked())

    if language is not None and language in _ALLOWED_LANGUAGES:
        if language is _DEFAULT_LANGUAGE:
            config_set(LANGUAGE, b'')
        else:
            config_set(LANGUAGE, language.encode())
    if label is not None:
        config_set(LABEL, label.encode())
    if pin is not None:
        config_set(PIN, pin.encode())
    if passphrase_protection is not None:
        config_set(PASSPHRASE_PROTECTION,
                   int_to_bytes(passphrase_protection))


def wipe():
    lock()
    config.wipe()


def new_device_id() -> str:
    from ubinascii import hexlify
    from trezor.crypto import random
    return hexlify(random.bytes(12)).decode('ascii').upper()


def config_get(key: int) -> bytes:
    return config.get(_APP, key)


def config_set(key: int, value: bytes):
    config.set(_APP, key, value)


def config_set_checked(key, value: bytes):
    config_set(key, value)
    check = config_get(key)
    if check != value:
        utils.halt('config.set failed')


# TODO: store ints as varints

def int_to_bytes(i: int) -> bytes:
    return ustruct.pack('>L', i) if i else bytes()


def bytes_to_int(b: bytes) -> int:
    return ustruct.unpack('>L', b)[0] if b else 0
