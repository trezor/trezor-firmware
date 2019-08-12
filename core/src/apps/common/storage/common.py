from trezor import config

if False:
    from typing import Optional

# Namespaces:
# fmt: off
# Intentionally not using const() to allow import in submodules.
_APP_DEVICE             = 0x01
_APP_RECOVERY           = 0x02
_APP_RECOVERY_SHARES    = 0x03
# fmt: on

_FALSE_BYTE = b"\x00"
_TRUE_BYTE = b"\x01"

_STORAGE_VERSION_01 = b"\x01"
_STORAGE_VERSION_CURRENT = b"\x02"


def _set(app: int, key: int, data: bytes, public: bool = False) -> None:
    config.set(app, key, data, public)


def _get(app: int, key: int, public: bool = False) -> Optional[bytes]:
    return config.get(app, key, public)


def _delete(app: int, key: int) -> None:
    config.delete(app, key)


def _set_true_or_delete(app: int, key: int, value: bool) -> None:
    if value:
        _set_bool(app, key, value)
    else:
        _delete(app, key)


def _set_bool(app: int, key: int, value: bool, public: bool = False) -> None:
    if value:
        _set(app, key, _TRUE_BYTE, public)
    else:
        _set(app, key, _FALSE_BYTE, public)


def _get_bool(app: int, key: int, public: bool = False) -> bool:
    return _get(app, key, public) == _TRUE_BYTE


def _set_uint8(app: int, key: int, val: int) -> None:
    _set(app, key, val.to_bytes(1, "big"))


def _get_uint8(app: int, key: int) -> Optional[int]:
    val = _get(app, key)
    if not val:
        return None
    return int.from_bytes(val, "big")


def _set_uint16(app: int, key: int, val: int) -> None:
    _set(app, key, val.to_bytes(2, "big"))


def _get_uint16(app: int, key: int) -> Optional[int]:
    val = _get(app, key)
    if not val:
        return None
    return int.from_bytes(val, "big")


def _set_uint32(app: int, key: int, val: int) -> None:
    _set(app, key, val.to_bytes(4, "big"))


def _get_uint32(app: int, key: int) -> Optional[int]:
    val = _get(app, key)
    if not val:
        return None
    return int.from_bytes(val, "big")


def _next_counter(app: int, key: int, public: bool = False) -> Optional[int]:
    return config.next_counter(app, key, public)


def _set_counter(app: int, key: int, count: int, public: bool = False) -> None:
    config.set_counter(app, key, count, public)
