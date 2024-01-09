from micropython import const

import storage.device

# backlight brightness
BACKLIGHT_NORMAL = const(150)
BACKLIGHT_LOW = const(45)
BACKLIGHT_DIM = const(5)
BACKLIGHT_NONE = const(0)
BACKLIGHT_MIN = const(10)
BACKLIGHT_MAX = const(255)


def get_backlight_normal() -> int:
    val = storage.device.get_brightness()
    if val is None:
        return BACKLIGHT_NORMAL
    return val


def get_backlight_low() -> int:
    val = storage.device.get_brightness()
    if val is None or val > BACKLIGHT_LOW:
        return BACKLIGHT_LOW
    return val
