from micropython import const

from trezor import config

if False:
    from typing import Optional

# Namespaces:
# fmt: off
APP_DEVICE             = const(0x01)
APP_RECOVERY           = const(0x02)
APP_RECOVERY_SHARES    = const(0x03)
APP_WEBAUTHN           = const(0x04)
# fmt: on

_FALSE_BYTE = b"\x00"
_TRUE_BYTE = b"\x01"

STORAGE_VERSION_01 = b"\x01"
STORAGE_VERSION_CURRENT = b"\x02"


def set(app: int, key: int, data: bytes, public: bool = False) -> None:
    config.set(app, key, data, public)


def get(app: int, key: int, public: bool = False) -> Optional[bytes]:
    return config.get(app, key, public)


def delete(app: int, key: int, public: bool = False) -> None:
    config.delete(app, key, public)


def set_true_or_delete(app: int, key: int, value: bool) -> None:
    if value:
        set_bool(app, key, value)
    else:
        delete(app, key)


def set_bool(app: int, key: int, value: bool, public: bool = False) -> None:
    if value:
        set(app, key, _TRUE_BYTE, public)
    else:
        set(app, key, _FALSE_BYTE, public)


def get_bool(app: int, key: int, public: bool = False) -> bool:
    return get(app, key, public) == _TRUE_BYTE


def set_uint8(app: int, key: int, val: int) -> None:
    set(app, key, val.to_bytes(1, "big"))


def get_uint8(app: int, key: int) -> Optional[int]:
    val = get(app, key)
    if not val:
        return None
    return int.from_bytes(val, "big")


def set_uint16(app: int, key: int, val: int) -> None:
    set(app, key, val.to_bytes(2, "big"))


def get_uint16(app: int, key: int) -> Optional[int]:
    val = get(app, key)
    if not val:
        return None
    return int.from_bytes(val, "big")


def next_counter(app: int, key: int, public: bool = False) -> Optional[int]:
    return config.next_counter(app, key, public)


def set_counter(app: int, key: int, count: int, public: bool = False) -> None:
    config.set_counter(app, key, count, public)
