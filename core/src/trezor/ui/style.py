from micropython import const

import storage.device

# backlight brightness
_BACKLIGHT_NORMAL = const(150)
_BACKLIGHT_LOW = const(45)
_BACKLIGHT_DIM = const(5)
_BACKLIGHT_NONE = const(0)
_BACKLIGHT_MIN = const(10)
_BACKLIGHT_MAX = const(255)


def get_backlight_normal() -> int:
    val = storage.device.get_brightness()
    if val is None:
        return _BACKLIGHT_NORMAL
    return val


def get_backlight_low() -> int:
    val = storage.device.get_brightness()
    if val is None or val > _BACKLIGHT_LOW:
        return _BACKLIGHT_LOW
    return val


def get_backlight_dim() -> int:
    return _BACKLIGHT_DIM


def get_backlight_none() -> int:
    return _BACKLIGHT_NONE


def get_backlight_min() -> int:
    return _BACKLIGHT_MIN


def get_backlight_max() -> int:
    return _BACKLIGHT_MAX
